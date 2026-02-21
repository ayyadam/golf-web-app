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

            for (let i = 1; i < size; i++) {
                const playerHtml = `
                    <div class="card-glass p-3 mb-3">
                        <h6 class="mb-3"><i class="bi bi-person me-2"></i>Player ${i + 1}</h6>
                        <div class="row g-3">
                            <div class="col-md-8">
                                <label class="form-label" for="player_${i}_name">Name</label>
                                <input type="text" class="form-control" id="player_${i}_name" 
                                       name="player_${i}_name" required>
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
        });
    }
});
