/**
 * Adam's Golf Club — Main JavaScript
 */

// ── Navbar scroll effect ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const navbar = document.getElementById('mainNav');

    if (navbar) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // ── Auto-dismiss flash messages ─────────────────────────────────────
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // ── Animate elements on scroll ──────────────────────────────────────
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });

    // ── Group size selector for booking forms ───────────────────────────
    const groupSizeSelect = document.getElementById('groupSize');
    const additionalPlayersDiv = document.getElementById('additionalPlayers');

    if (groupSizeSelect && additionalPlayersDiv) {
        groupSizeSelect.addEventListener('change', () => {
            const size = parseInt(groupSizeSelect.value);
            additionalPlayersDiv.innerHTML = '';

            // Render descending z-index to ensure dropdown menus overlap cards below them
            for (let i = 1; i < size; i++) {
                const zIndex = 100 - i;
                const playerHtml = `
                    <div class="card-glass p-3 mb-3" style="position: relative; overflow: visible; z-index: ${zIndex};">
                        <h6 class="mb-3"><i class="bi bi-person me-2"></i>Player ${i + 1}</h6>
                        <div class="row g-3">
                            <div class="col-md-8 position-relative">
                                <label class="form-label" for="player_${i}_name">Name 
                                    <small class="text-muted fw-normal">(Type to search members or type visitor name)</small>
                                </label>
                                <div class="position-relative">
                                    <input type="text" class="form-control member-autocomplete pr-4" id="player_${i}_name" 
                                           name="player_${i}_name" data-index="${i}" autocomplete="off" required>
                                    <button type="button" class="btn-close position-absolute top-50 end-0 translate-middle-y me-2 d-none" 
                                            id="clear_player_${i}" aria-label="Clear"></button>
                                </div>
                                <ul class="dropdown-menu w-100 autocomplete-results" id="autocomplete_results_${i}"></ul>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label" for="player_${i}_handicap">Handicap</label>
                                <input type="number" class="form-control" id="player_${i}_handicap" 
                                       name="player_${i}_handicap" step="0.1" min="0" max="54">
                            </div>
                        </div>
                    </div>
                `;
                additionalPlayersDiv.insertAdjacentHTML('beforeend', playerHtml);
            }

            // Attach autocomplete event listeners to new inputs
            document.querySelectorAll('.member-autocomplete').forEach(input => {
                const index = input.getAttribute('data-index');
                const clearBtn = document.getElementById(`clear_player_${index}`);
                const hcInput = document.getElementById(`player_${index}_handicap`);

                // Action when user clicks the 'X' button
                clearBtn.addEventListener('click', () => {
                    input.value = '';
                    hcInput.value = '';
                    hcInput.readOnly = false;
                    clearBtn.classList.add('d-none');
                    document.getElementById(`autocomplete_results_${index}`).classList.remove('show');
                    input.focus();
                });

                input.addEventListener('input', async function () {
                    const query = this.value.trim();
                    const index = this.getAttribute('data-index');
                    const resultsUl = document.getElementById(`autocomplete_results_${index}`);

                    // If the user starts typing again after selecting a member, unlock the handicap
                    hcInput.readOnly = false;

                    // Toggle clear button
                    if (query.length > 0) {
                        clearBtn.classList.remove('d-none');
                    } else {
                        clearBtn.classList.add('d-none');
                    }

                    if (query.length < 1) {
                        resultsUl.classList.remove('show');
                        return;
                    }

                    try {
                        const response = await fetch(`/member/api/members/search?q=${encodeURIComponent(query)}`);
                        if (!response.ok) throw new Error("Network response was not ok");
                        const data = await response.json();

                        // Filter out members already selected in other inputs
                        const activeNames = Array.from(document.querySelectorAll('.member-autocomplete'))
                            .filter(inp => inp.getAttribute('data-index') !== index && inp.value.trim() !== '')
                            .map(inp => inp.value.trim().toLowerCase());

                        resultsUl.innerHTML = '';

                        if (data.members && data.members.length > 0) {
                            const filteredMembers = data.members.filter(m => !activeNames.includes(m.name.toLowerCase()));

                            if (filteredMembers.length > 0) {
                                filteredMembers.forEach(member => {
                                    const li = document.createElement('li');
                                    li.innerHTML = `<a class="dropdown-item" href="#" style="cursor:pointer">
                                        <div class="fw-bold">${member.name}</div>
                                        <small class="text-muted">Handicap: ${member.handicap !== null ? member.handicap : 'None'}</small>
                                    </a>`;

                                    li.addEventListener('click', (e) => {
                                        e.preventDefault();
                                        this.value = member.name;

                                        if (hcInput && member.handicap !== null) {
                                            hcInput.value = member.handicap;
                                            hcInput.readOnly = true;
                                        } else if (hcInput) {
                                            hcInput.value = '';
                                            hcInput.readOnly = false;
                                        }

                                        // Ensure clear button is visible for the selected member
                                        clearBtn.classList.remove('d-none');
                                        resultsUl.classList.remove('show');
                                    });

                                    resultsUl.appendChild(li);
                                });
                                resultsUl.classList.add('show');
                            } else {
                                resultsUl.classList.remove('show');
                            }
                        } else {
                            resultsUl.classList.remove('show');
                        }
                    } catch (error) {
                        console.error('Error fetching members:', error);
                    }
                });

                // Hide dropdown when clicking outside
                document.addEventListener('click', function (e) {
                    const index = input.getAttribute('data-index');
                    const resultsUl = document.getElementById(`autocomplete_results_${index}`);
                    if (resultsUl && !input.contains(e.target) && !resultsUl.contains(e.target)) {
                        resultsUl.classList.remove('show');
                    }
                });
            });
        });
    }
});
