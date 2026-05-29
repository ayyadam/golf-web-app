"""Natural-language booking assistant.

Turns a member's free-text request ("book a 4-ball Saturday morning") into a
structured BookingIntent, then finds matching tee-time slots. The language
model ONLY produces the structured intent — it never books anything. The
deterministic code here (and the existing booking_service) validates and
executes, with a human confirming the chosen slot. That boundary is the
safety control against hallucinated or injected instructions.

Providers are pluggable: the model/provider is chosen from environment via a
registry, so swapping Ollama for another backend (or changing the model) is a
config change, and adding a provider is one new class implementing `_complete`.
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Optional, Protocol

# ── Structured intent ─────────────────────────────────────────────────────

VALID_PERIODS = ("morning", "afternoon", "any")
MIN_GROUP, MAX_GROUP = 1, 4


@dataclass
class BookingIntent:
    """What the member wants, in structured form. The only thing a model emits."""
    date: date
    period: str = "any"          # 'morning' | 'afternoon' | 'any'
    group_size: int = 1
    players: list[str] = field(default_factory=list)
    not_before: Optional[time] = None   # earliest acceptable tee time ("from 9am")
    not_after: Optional[time] = None    # latest acceptable tee time ("by 11am")


class IntentParseError(ValueError):
    """Raised when free text cannot be turned into a valid BookingIntent."""


def _coerce_clock(value) -> Optional[time]:
    """Parse a provider's "HH:MM" time string into a time, or None.

    A bad or missing value drops the constraint (returns None) rather than
    failing the whole intent — a malformed time bound should not stop us
    proposing slots.
    """
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value
    try:
        return datetime.strptime(str(value).strip(), "%H:%M").time()
    except ValueError:
        return None


def _coerce_intent(raw: dict) -> BookingIntent:
    """Validate a raw provider dict into a BookingIntent, or raise.

    Shared by every LLM provider so they are interchangeable: each provider
    only has to return a dict shaped like the intent; validation lives here.
    """
    try:
        d = raw["date"]
        parsed_date = d if isinstance(d, date) else datetime.strptime(str(d), "%Y-%m-%d").date()
    except (KeyError, TypeError, ValueError) as exc:
        raise IntentParseError(f"Could not read a valid date from intent: {raw!r}") from exc

    period = str(raw.get("period", "any")).lower().strip()
    if period not in VALID_PERIODS:
        period = "any"

    try:
        group_size = int(raw.get("group_size", 1))
    except (TypeError, ValueError):
        group_size = 1
    group_size = max(MIN_GROUP, min(MAX_GROUP, group_size))

    players_raw = raw.get("players") or []
    players = [p.strip() for p in players_raw if isinstance(p, str) and p.strip()]

    return BookingIntent(
        date=parsed_date,
        period=period,
        group_size=group_size,
        players=players,
        not_before=_coerce_clock(raw.get("not_before")),
        not_after=_coerce_clock(raw.get("not_after")),
    )


# ── Extractor interface + implementations ─────────────────────────────────

class IntentExtractor(Protocol):
    """Anything that can turn free text into a BookingIntent."""

    def extract(self, text: str) -> BookingIntent: ...


_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "single": 1}

# A spoken clock token: "9", "9:30", "2pm", "11 am", "noon".
_TIME_PAT = r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?|noon|midday|midnight)"
_CLOCK_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$")


def _parse_clock_token(tok: str) -> Optional[time]:
    """Best-effort parse of a spoken clock token into a time, or None."""
    tok = tok.strip().lower()
    if tok in ("noon", "midday"):
        return time(12, 0)
    if tok == "midnight":
        return time(0, 0)
    m = _CLOCK_RE.match(tok)
    if not m:
        return None
    hour, mins, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if mins > 59:
        return None
    if ap == "pm" and hour != 12:
        hour += 12
    elif ap == "am" and hour == 12:
        hour = 0
    return time(hour, mins) if hour <= 23 else None


class StubIntentExtractor:
    """Deterministic, rule-based fake — no model. Used in CI so the gates stay
    fast and reproducible. Good enough to exercise the plumbing; it makes no
    claim to understand messy language (that is the model's job, assessed in
    the evaluation harness)."""

    def extract(self, text: str, today: Optional[date] = None) -> BookingIntent:
        today = today or date.today()
        t = (text or "").lower()

        # group size: "4-ball"/"four ball"/digit/number word, else 1
        group_size = 1
        m = re.search(r"\b([1-4])\s*[- ]?\s*ball\b", t) or re.search(r"\b([1-4])\b", t)
        if m:
            group_size = int(m.group(1))
        else:
            for word, n in _NUMBER_WORDS.items():
                if re.search(rf"\b{word}\b", t):
                    group_size = n
                    break

        period = "morning" if "morning" in t else "afternoon" if ("afternoon" in t or "evening" in t) else "any"

        when = today
        if "tomorrow" in t:
            when = today + timedelta(days=1)
        elif "today" in t:
            when = today
        else:
            for name, wd in _WEEKDAYS.items():
                if name in t:
                    ahead = (wd - today.weekday()) % 7
                    when = today + timedelta(days=ahead)
                    break

        not_before = not_after = None
        between = re.search(rf"\bbetween\s+{_TIME_PAT}\s+and\s+{_TIME_PAT}", t)
        if between:
            not_before = _parse_clock_token(between.group(1))
            not_after = _parse_clock_token(between.group(2))
        else:
            after = re.search(rf"\b(?:from|after|no earlier than)\s+{_TIME_PAT}", t)
            if after:
                not_before = _parse_clock_token(after.group(1))
            before = re.search(rf"\b(?:before|by|no later than|until)\s+{_TIME_PAT}", t)
            if before:
                not_after = _parse_clock_token(before.group(1))
            if not_before is None and not_after is None:
                at = re.search(rf"\bat\s+{_TIME_PAT}", t)
                if at:
                    not_before = not_after = _parse_clock_token(at.group(1))

        return _coerce_intent({
            "date": when, "period": period, "group_size": group_size,
            "not_before": not_before, "not_after": not_after,
        })


_INTENT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "date": {"type": "string", "description": "absolute date as YYYY-MM-DD"},
        "period": {"type": "string", "enum": list(VALID_PERIODS)},
        "group_size": {"type": "integer", "minimum": MIN_GROUP, "maximum": MAX_GROUP},
        "players": {"type": "array", "items": {"type": "string"}},
        "not_before": {
            "type": ["string", "null"],
            "description": "earliest acceptable tee time as HH:MM 24-hour, or null",
        },
        "not_after": {
            "type": ["string", "null"],
            "description": "latest acceptable tee time as HH:MM 24-hour, or null",
        },
    },
    "required": ["date", "period", "group_size"],
}


class LLMIntentExtractor(ABC):
    """Base for model-backed extractors. Owns the prompt, JSON parsing and
    validation so concrete providers only implement the transport call."""

    def extract(self, text: str, today: Optional[date] = None) -> BookingIntent:
        today = today or date.today()
        raw = self._complete(self._system_prompt(today), text or "")
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise IntentParseError(f"Model did not return valid JSON: {raw!r}") from exc
        return _coerce_intent(data)

    @staticmethod
    def _system_prompt(today: date) -> str:
        # An explicit calendar makes relative-date resolution ("this Saturday",
        # "next Friday") reliable across models, rather than relying on the model
        # to do weekday arithmetic in its head.
        calendar = "\n".join(
            f"{(today + timedelta(days=i)).isoformat()} {(today + timedelta(days=i)).strftime('%A')}"
            + (" (today)" if i == 0 else "")
            for i in range(10)
        )
        return (
            "You convert a golf club member's natural-language tee-time request into JSON.\n"
            "Resolve any relative date (today, tomorrow, 'this Saturday', 'next Friday') to an "
            "absolute YYYY-MM-DD using this calendar:\n"
            f"{calendar}\n"
            "When only a weekday is named, pick the SOONEST row in the calendar whose weekday "
            "matches exactly. Copy that row's date verbatim.\n"
            "period is 'morning' (before 12:00), 'afternoon' (12:00 or later), or 'any'. "
            "group_size is the number of players from 1 to 4. "
            "players is the list of named playing partners mentioned, excluding the member.\n"
            "If a specific time or time range is given, also set not_before and/or "
            "not_after as HH:MM 24-hour; otherwise leave them null:\n"
            "  'from 9am' / 'after 9' / 'no earlier than 9' -> not_before '09:00'\n"
            "  'before noon' / 'by 11am' / 'no later than 3pm' -> not_after '12:00' / '11:00' / '15:00'\n"
            "  'between 9 and 11' -> not_before '09:00', not_after '11:00'\n"
            "  'at 10am' -> not_before '10:00' and not_after '10:00'\n"
            "Convert 12-hour times to 24-hour. period is the half-day and may be "
            "combined with these bounds.\n"
            "Respond with only the JSON object."
        )

    @abstractmethod
    def _complete(self, system_prompt: str, user_text: str) -> str:
        """Return the model's raw text response (expected to be JSON)."""


class OllamaIntentExtractor(LLMIntentExtractor):
    """Local Ollama provider. Only the transport lives here."""

    def __init__(self, model: Optional[str] = None, host: Optional[str] = None):
        self.model = model or os.getenv("BOOKING_ASSISTANT_MODEL", "qwen3:8b-fp16")
        self.host = host or os.getenv("OLLAMA_HOST")

    def _complete(self, system_prompt: str, user_text: str) -> str:
        import ollama  # lazy: only needed when this provider is actually used

        client = ollama.Client(host=self.host) if self.host else ollama
        kwargs = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            format=_INTENT_JSON_SCHEMA,   # structured output: constrain to the intent shape
            options={"temperature": 0},   # low temperature for stable extraction
        )
        # think=False keeps qwen3-style models fast and direct. Models without a
        # thinking mode reject the flag, so fall back to a call without it.
        try:
            response = client.chat(think=False, **kwargs)
        except ollama.ResponseError:
            response = client.chat(**kwargs)
        return response["message"]["content"]


# ── Provider registry ─────────────────────────────────────────────────────

_PROVIDERS: dict[str, type] = {
    "stub": StubIntentExtractor,
    "ollama": OllamaIntentExtractor,
}


def get_intent_extractor() -> IntentExtractor:
    """Select the extractor from BOOKING_ASSISTANT_PROVIDER (default: stub).

    Defaulting to the stub means no model is required to run the app or its
    deterministic tests; set the env var to 'ollama' to use the real model.
    """
    name = os.getenv("BOOKING_ASSISTANT_PROVIDER", "stub").lower()
    return _PROVIDERS.get(name, StubIntentExtractor)()


# ── Deterministic slot matching ───────────────────────────────────────────

def _matches_period(slot_time: time, period: str) -> bool:
    if period == "morning":
        return slot_time < time(12, 0)
    if period == "afternoon":
        return slot_time >= time(12, 0)
    return True


def _matches_time_window(slot_time: time, intent: BookingIntent) -> bool:
    """Apply the member's explicit time bounds (inclusive), if any."""
    if intent.not_before is not None and slot_time < intent.not_before:
        return False
    if intent.not_after is not None and slot_time > intent.not_after:
        return False
    return True


def find_candidate_slots(intent: BookingIntent, member=None, limit: Optional[int] = None):
    """Return bookable tee-time slots matching the intent, earliest first.

    Reuses the same availability rules as the member booking page (past-time
    and competition-day filtering) so proposed slots are genuinely bookable,
    and preserves its earliest-first ordering. When a member is given, slots
    they are already booked on are excluded. With no limit, every matching
    slot is returned so the member sees the full availability they asked for
    rather than a silently truncated subset; pass a limit only to cap the list.
    """
    from ..routes.member import _filter_available_tee_times

    slots = _filter_available_tee_times(intent.date)
    matching = [
        s for s in slots
        if _matches_period(s.time, intent.period)
        and _matches_time_window(s.time, intent)
        and s.slots_remaining >= intent.group_size
    ]

    if member is not None:
        from ..extensions import db
        from ..models import BookingPlayer, GeneralBooking, TeeTime

        already_booked = {
            b.tee_time_id
            for b in GeneralBooking.query.join(TeeTime).filter(
                TeeTime.date == intent.date,
                db.or_(
                    GeneralBooking.member_id == member.id,
                    GeneralBooking.players.any(BookingPlayer.player_name == member.full_name),
                ),
            ).all()
        }
        matching = [s for s in matching if s.id not in already_booked]

    return matching if limit is None else matching[:limit]
