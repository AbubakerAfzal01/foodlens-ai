
/* ============================================================
   CONTENT PROTECTION
   FoodLens AI
   Deterrent only — not actual security.
============================================================ */

(function () {
  const PROTECT_MSG = '⚠️ Content is protected. Copying is disabled.';

  let toastTimer = null;
  let accessDeniedTimer = null;

  // ---------------------------------------------------------
  // Toast Notification
  // ---------------------------------------------------------

  function ensureToastEl() {
    let el = document.getElementById('protectToast');

    if (!el) {
      el = document.createElement('div');
      el.id = 'protectToast';
      document.body.appendChild(el);
    }

    return el;
  }

  function showProtectionToast(msg) {
    const el = ensureToastEl();

    el.textContent = msg || PROTECT_MSG;
    el.classList.add('show');

    clearTimeout(toastTimer);

    toastTimer = setTimeout(() => {
      el.classList.remove('show');
    }, 2000);
  }

  // ---------------------------------------------------------
  // Access Denied Modal
  // ---------------------------------------------------------

  function ensureAccessDeniedEl() {
    let el = document.getElementById('accessDeniedOverlay');

    if (!el) {
      el = document.createElement('div');

      el.id = 'accessDeniedOverlay';

      el.innerHTML = `
        <div class="accessDeniedBox">
          ACCESS DENIED
          <span class="accessDeniedSub">
            CONTENT PROTECTION ACTIVE
          </span>
        </div>
      `;

      document.body.appendChild(el);
    }

    return el;
  }

  function showAccessDenied(duration = 1500) {
    const el = ensureAccessDeniedEl();

    el.classList.add('show');

    clearTimeout(accessDeniedTimer);

    accessDeniedTimer = setTimeout(() => {
      el.classList.remove('show');
    }, duration);
  }

  // ---------------------------------------------------------
  // Combined Protection Trigger
  // ---------------------------------------------------------

  function triggerProtection(toastMsg, modalDuration = 1500) {
    showAccessDenied(modalDuration);

    setTimeout(() => {
      showProtectionToast(toastMsg);
    }, modalDuration);
  }

  // ---------------------------------------------------------
  // Detect Form Fields
  // ---------------------------------------------------------

  function isFormField(el) {
    if (!el) return false;

    return (
      el.tagName === 'INPUT' ||
      el.tagName === 'TEXTAREA' ||
      el.tagName === 'SELECT' ||
      el.isContentEditable
    );
  }

  // ---------------------------------------------------------
  // 1. Right Click Protection
  // ---------------------------------------------------------

  document.addEventListener('contextmenu', function (e) {
    if (isFormField(e.target)) return;

    e.preventDefault();
    triggerProtection();
  });

  // ---------------------------------------------------------
  // 2. Keyboard Shortcut Protection
  // ---------------------------------------------------------

  document.addEventListener('keydown', function (e) {
    const key = (e.key || '').toLowerCase();
    const ctrlOrCmd = e.ctrlKey || e.metaKey;

    // F12
    if (key === 'f12') {
      e.preventDefault();
      triggerProtection();
      return;
    }

    // DevTools shortcuts
    if (
      ctrlOrCmd &&
      e.shiftKey &&
      ['i', 'j', 'c'].includes(key)
    ) {
      e.preventDefault();
      triggerProtection();
      return;
    }

    // View Source / Save Page
    if (
      ctrlOrCmd &&
      !e.shiftKey &&
      ['u', 's'].includes(key)
    ) {
      e.preventDefault();
      triggerProtection();
      return;
    }

    // Copy / Cut outside form fields
    if (
      ctrlOrCmd &&
      !e.shiftKey &&
      ['c', 'x'].includes(key) &&
      !isFormField(e.target)
    ) {
      e.preventDefault();
      triggerProtection();
    }
  });

  // ---------------------------------------------------------
  // 3. Image Drag Protection
  // ---------------------------------------------------------

  document.addEventListener('dragstart', function (e) {
    if (e.target?.tagName === 'IMG') {
      e.preventDefault();
      triggerProtection();
    }
  });

  function hardenImages() {
    document.querySelectorAll('img').forEach(function (img) {
      img.setAttribute('draggable', 'false');
    });
  }

  hardenImages();

  new MutationObserver(hardenImages).observe(document.body, {
    childList: true,
    subtree: true
  });

  // ---------------------------------------------------------
  // Expose Functions
  // ---------------------------------------------------------

  window.showProtectionToast = showProtectionToast;
  window.showAccessDenied = showAccessDenied;
  window.triggerProtection = triggerProtection;

})();
