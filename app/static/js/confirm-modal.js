/* ═══════════════════════════════════════════════════════════════════════════
   AGC Confirm Modal — replaces browser confirm() dialogs
   Usage:  <form onsubmit="return confirmAction(this, 'Your message here')">
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    /** Show a custom confirm modal. Returns false to cancel the form submit;
     *  the modal's "Confirm" button will re-submit the form bypassing this check. */
    window.confirmAction = function (formEl, message) {
        // If the form was already confirmed, let it through
        if (formEl.dataset.confirmed === 'true') {
            formEl.dataset.confirmed = '';
            return true;
        }

        var modal = document.getElementById('agcConfirmModal');
        var msgEl = document.getElementById('agcConfirmMessage');
        var btnConfirm = document.getElementById('agcConfirmBtn');
        var btnCancel = document.getElementById('agcCancelBtn');

        msgEl.textContent = message;

        // Show modal
        modal.classList.add('active');

        // Clone button to strip old listeners
        var newBtn = btnConfirm.cloneNode(true);
        btnConfirm.parentNode.replaceChild(newBtn, btnConfirm);

        newBtn.addEventListener('click', function () {
            modal.classList.remove('active');
            formEl.dataset.confirmed = 'true';
            formEl.submit();
        });

        // Cancel
        var newCancel = btnCancel.cloneNode(true);
        btnCancel.parentNode.replaceChild(newCancel, btnCancel);
        newCancel.addEventListener('click', function () {
            modal.classList.remove('active');
        });

        // Click backdrop to cancel
        modal.addEventListener('click', function handler(e) {
            if (e.target === modal) {
                modal.classList.remove('active');
                modal.removeEventListener('click', handler);
            }
        });

        return false; // prevent default submit
    };
})();
