
const guild_switcher = document.querySelector('.guild-selector')
guild_switcher.addEventListener('click', function() {
  guild_switcher.classList.toggle('active');
});

function TooltipText(e, txt) {
  navigator.clipboard.writeText(txt);

  e.querySelector('.tooltiptext').innerHTML = 'Copied'
  setTimeout(() => {
    e.querySelector('.tooltiptext').innerHTML = 'Copy'
  }, 2000)
}

// Navbar - side menu
var navbar_item = document.querySelectorAll('.navbar-item');

window.addEventListener('load', function() {
  var currentURL = window.location.pathname;

  navbar_item.forEach((item) => {
    var itemURL = item.querySelector('.navbar-link').dataset.href
    var isActive = itemURL === currentURL;

    item.dataset.active = isActive ? "True" : "False";
  });
});

navbar_item.forEach((item) => {
  item.addEventListener('click', (e) => {
    var currentURL = window.location.pathname;
    var link = item.querySelector('.navbar-link')

    const isModulePrem = link.dataset.modulePremium // is the plugin premium
    const isPremium = link.dataset.isPremium // server check - True if hasPrem else False

    if (isModulePrem === 'True' && isPremium === 'False') {
      const PremiumModal = new bootstrap.Modal(document.getElementById('PremiumModal'));
      PremiumModal.show();
    } else {
      var url = link.dataset.href;
      var isActive = url === currentURL;
      e.target.dataset.active = isActive ? "True" : "False";

      document.location.href = url;
    }
  });
});

function handlePremiumOnClick(event) {
  const link = event.currentTarget;
  const isPluginPremium = link.dataset.premium === 'true';
  const serverHasPremium = link.dataset.serverPremium === 'true';

  if (isPluginPremium && !serverHasPremium) {
    new bootstrap.Modal(document.getElementById('PremiumModal')).show();
    return;
  }

  if (link.dataset.enabled === 'false' && window.PluginDisabledModal) {
    window.PluginDisabledModal.open({
      key: link.dataset.key,
      name: link.dataset.pluginName,
      href: '/dashboard/' + link.dataset.href,
    });
    return;
  }

  document.location.href = link.dataset.href;
}

// ── Disabled-plugin handling ───────────────────────────────────────────────
/* Two behaviours for a plugin whose main status toggle is off:
   - clicking it (sidebar link / dashboard card) -> confirm modal, "Activate"
     flips <db_key>.status then opens the plugin.
   - landing straight on its page URL -> enable it silently on load and patch
     the toggle + sidebar indicator in place (no reload).
   Enabling goes through the existing data/post endpoint. UX only - the backend
   must still gate. */
(function () {
  const modalEl = document.getElementById('PluginDisabledModal');
  if (!modalEl || typeof bootstrap === 'undefined') return;

  const guildId = modalEl.dataset.guildId;
  const homePath = '/dashboard/' + guildId;
  const nameEls = modalEl.querySelectorAll('.pdm-plugin-name');
  const activateBtn = document.getElementById('pdm-activate');
  const activateHTML = activateBtn ? activateBtn.innerHTML : 'Activate';
  const bsModal = new bootstrap.Modal(modalEl, { backdrop: 'static', keyboard: false });

  let pending = null; // { key, name, href }
  let navigating = false;

  function go(url) {
    navigating = true;
    window.location.href = url;
  }

  function open(info) {
    if (!info || !info.key) return;
    pending = info;
    nameEls.forEach(function (el) { el.textContent = info.name || 'this plugin'; });
    bsModal.show();
  }
  window.PluginDisabledModal = { open: open };

  // Flip <key>.status -> true via the catch-all config endpoint.
  async function enablePlugin(key) {
    const res = await fetch(homePath + '/data/post', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [key + '.status']: true }),
    });
    const body = await res.json().catch(function () { return {}; });
    if (!res.ok || body.status === 'error') {
      throw new Error(body.message || 'Failed to enable plugin');
    }
  }

  // Sidebar links carry data-key only on real plugins (not settings/premium/dashboard)
  const pluginLinks = document.querySelectorAll('#sidebar-nav .navbar-link[data-key][data-href]');

  function isPremiumLocked(el) {
    return el.dataset.modulePremium === 'True' && el.dataset.isPremium === 'False';
  }
  function infoFromLink(link) {
    return { key: link.dataset.key, name: link.dataset.plugin, href: link.dataset.href };
  }

  // 1. Direct navigation to a disabled plugin page (or one of its sub-pages):
  //    enable it silently and patch the UI in place - no reload. Plugin pages
  //    only use the status to set the main toggle's checked state, so flipping
  //    that plus the sidebar indicator is enough. On failure, show the modal.
  document.addEventListener('DOMContentLoaded', function () {
    const path = window.location.pathname;
    let link = null;
    for (const l of pluginLinks) {
      const href = l.dataset.href;
      if (path === href || path.startsWith(href + '/')) { link = l; break; }
    }
    if (!link || link.dataset.enable !== 'False' || isPremiumLocked(link)) return;

    enablePlugin(link.dataset.key)
      .then(function () {
        link.setAttribute('data-enable', 'True');
        const toggle = document.querySelector("input[role='switch'][name='plugin-status']");
        if (toggle) toggle.checked = true;
      })
      .catch(function () { open(infoFromLink(link)); });
  });

  // 2. Clicking a disabled plugin in the sidebar - capture so we beat the
  //    navigation handler bound to the parent <li class="navbar-item">
  pluginLinks.forEach(function (link) {
    link.addEventListener('click', function (e) {
      if (link.dataset.enable !== 'False' || isPremiumLocked(link)) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      open(infoFromLink(link));
    }, true);
  });

  // 3. Dashboard plugin cards are handled inline by handlePremiumOnClick()

  // Dismissing the modal (Cancel / X / Esc) leaves nowhere to go on a disabled
  // plugin page, so bounce back to the dashboard home unless we're activating.
  modalEl.addEventListener('hidden.bs.modal', function () {
    if (!navigating && window.location.pathname !== homePath) go(homePath);
  });

  if (activateBtn) {
    activateBtn.addEventListener('click', async function () {
      if (!pending || !pending.key) return;
      activateBtn.disabled = true;
      activateBtn.textContent = 'Activating…';
      try {
        await enablePlugin(pending.key);
        go(pending.href);
      } catch (err) {
        activateBtn.disabled = false;
        activateBtn.innerHTML = activateHTML;
        alert(err.message || 'Could not enable this plugin. Please try again.');
      }
    });
  }
})();

/* ── Sidebar plugin hover card ─────────────────────────────────────────────────
   Hover a sidebar plugin -> floating card with its name + description, and an
   "Upgrade your Server" CTA only when the plugin is premium and the guild is
   not. Mouse: shows on hover. Touch: a plain tap opens the plugin as normal;
   holding a row down shows this as a peek instead (see hold-to-preview below). */
(function () {
  const card = document.getElementById('PluginHoverCard');
  const nav = document.getElementById('sidebar-nav');
  if (!card || !nav) return;

  const iconEl = card.querySelector('.phc-icon');
  const titleEl = card.querySelector('.phc-title');
  const descEl = card.querySelector('.phc-desc');
  const upgradeEl = card.querySelector('.phc-upgrade');
  const includedEl = card.querySelector('.phc-included');

  let hideTimer = null;
  let active = null;

  function place(link) {
    const r = link.getBoundingClientRect();
    const cw = card.offsetWidth;
    const ch = card.offsetHeight;

    // Below the Bootstrap lg breakpoint the sidebar is a full-width mobile
    // overlay, so placing the card beside the row (like desktop) doesn't
    // work - sit it above the row instead, caret pointing down at it.
    if (window.matchMedia('(max-width: 991.98px)').matches) {
      card.classList.remove('phc-flip');

      let left = r.left + r.width / 2 - cw / 2;
      left = Math.max(12, Math.min(left, window.innerWidth - cw - 12));

      let top = r.top - ch - 6;
      const below = top < 12;
      if (below) top = r.bottom + 6;
      top = Math.max(12, Math.min(top, window.innerHeight - ch - 12));

      card.classList.toggle('phc-above', !below);
      card.classList.toggle('phc-below', below);
      card.style.top = top + 'px';
      card.style.left = left + 'px';
      const caretLeft = r.left + r.width / 2 - left;
      card.style.setProperty('--phc-caret-left', Math.max(12, Math.min(caretLeft, cw - 12)) + 'px');
      return;
    }
    card.classList.remove('phc-above', 'phc-below');

    let top = r.top + r.height / 2 - ch / 2;
    top = Math.max(12, Math.min(top, window.innerHeight - ch - 12));

    let left = r.right + 12;
    const flip = left + cw > window.innerWidth - 12;
    if (flip) left = Math.max(12, r.left - cw - 12);

    card.classList.toggle('phc-flip', flip);
    card.style.top = top + 'px';
    card.style.left = left + 'px';
    // keep the caret aligned with the row's centre even when the card is clamped
    const caretTop = r.top + r.height / 2 - top;
    card.style.setProperty('--phc-caret-top', Math.max(12, Math.min(caretTop, ch - 12)) + 'px');
  }

  function show(link) {
    clearTimeout(hideTimer);
    active = link;

    iconEl.textContent = link.dataset.icon || 'extension';
    titleEl.textContent = link.dataset.plugin || 'Plugin';
    descEl.textContent = link.dataset.desc || '';
    descEl.hidden = !link.dataset.desc;

    const premiumPlugin = link.dataset.modulePremium === 'True';
    const guildPremium = link.dataset.isPremium === 'True';
    upgradeEl.hidden = !(premiumPlugin && !guildPremium);
    includedEl.hidden = !(premiumPlugin && guildPremium);

    card.hidden = false;
    place(link);
    requestAnimationFrame(function () { card.classList.add('is-visible'); });
  }

  function scheduleHide() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(function () {
      active = null;
      card.classList.remove('is-visible');
      setTimeout(function () {
        if (!card.classList.contains('is-visible')) card.hidden = true;
      }, 140);
    }, 120);
  }

  nav.querySelectorAll('.navbar-item.plugin > .navbar-link[data-key]').forEach(function (link) {
    link.addEventListener('pointerenter', function (e) { if (e.pointerType === 'mouse') show(link); });
    link.addEventListener('pointerleave', function (e) { if (e.pointerType === 'mouse') scheduleHide(); });
  });
  card.addEventListener('pointerenter', function (e) { if (e.pointerType === 'mouse') clearTimeout(hideTimer); });
  card.addEventListener('pointerleave', function (e) { if (e.pointerType === 'mouse') scheduleHide(); });
  window.addEventListener('scroll', function () {
    if (active) { card.classList.remove('is-visible'); card.hidden = true; active = null; }
  }, true);

  // Touch has no hover, so give it a hold-to-preview gesture instead: a plain
  // tap opens the plugin as normal (untouched, no interception); holding a
  // row down for HOLD_MS shows this same card (desc + premium status) as a
  // peek, and releasing dismisses it without navigating anywhere.
  const HOLD_MS = 50;
  const MOVE_TOLERANCE = 15; // px of finger drift before we call it a scroll, not a hold
  let holdTimer = null;
  let holdLink = null;
  let holdStart = null;
  let holdActive = false; // true once HOLD_MS has elapsed and the preview is showing
  let suppressClickFor = null;

  function clearHold() {
    clearTimeout(holdTimer);
    holdTimer = null;
    holdLink = null;
    holdStart = null;
  }

  nav.addEventListener('pointerdown', function (e) {
    if (e.pointerType !== 'touch') return;
    const link = e.target.closest('.navbar-item.plugin > .navbar-link[data-key]');
    if (!link) return;
    clearHold();
    holdLink = link;
    holdStart = { x: e.clientX, y: e.clientY };
    holdActive = false;
    holdTimer = setTimeout(function () {
      holdActive = true;
      show(link);
    }, HOLD_MS);
  }, true);

  nav.addEventListener('pointermove', function (e) {
    if (e.pointerType !== 'touch' || !holdStart) return;
    const dx = e.clientX - holdStart.x;
    const dy = e.clientY - holdStart.y;
    if (Math.hypot(dx, dy) > MOVE_TOLERANCE) clearHold();
  }, true);

  nav.addEventListener('pointerup', function (e) {
    if (e.pointerType !== 'touch') return;
    const link = holdLink;
    const wasHold = holdActive;
    clearHold();
    holdActive = false;
    if (wasHold && link) {
      // this release was ending a hold-preview, not a tap - don't navigate
      suppressClickFor = link;
      scheduleHide();
    }
  }, true);

  nav.addEventListener('pointercancel', function () {
    clearHold();
    holdActive = false;
  }, true);

  nav.addEventListener('click', function (e) {
    const link = e.target.closest('.navbar-item.plugin > .navbar-link[data-key]');
    if (link && suppressClickFor === link) {
      e.preventDefault();
      e.stopImmediatePropagation();
      suppressClickFor = null;
    }
  }, true);
})();

try {
  var Switch = document.querySelector("input[role='switch'][name='plugin-status']")
  if (Switch) {
    Switch.addEventListener('change', (e) => {
      // Keep the sidebar link's data-enable in sync so the disabled-plugin
      // modal sees the fresh value without a page reload.
      const navBarLink = document.querySelector(
        `#sidebar-nav .navbar-link[data-href="${window.location.pathname}"]`
      );
      if (navBarLink) {
        navBarLink.setAttribute('data-enable', e.target.checked ? 'True' : 'False');
      }
    })
  }
} catch (error) {}