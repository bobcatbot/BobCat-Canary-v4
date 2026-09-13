/**
 * Variable autocomplete for message/embed text fields.
 *
 * Typing `{` inside any text input or textarea on a page that has the
 * Variables modal (components/variables.html) pops up a filterable list of
 * `{variable}` tags — pulled straight from that modal so there's a single
 * source of truth for names/descriptions. Arrow keys move the highlight,
 * Enter/Tab/click inserts the tag, Escape dismisses.
 */
(function () {
  const modal = document.getElementById('VariablesModal');
  if (!modal) return; // page doesn't use variables — nothing to do

  const VARIABLES = Array.from(modal.querySelectorAll('h5')).map((h5) => {
    const desc = h5.nextElementSibling;
    return {
      tag: h5.textContent.trim(), // e.g. "{server.name}"
      desc: desc ? desc.textContent.trim() : '',
    };
  }).filter((v) => v.tag.startsWith('{') && v.tag.endsWith('}'));

  if (!VARIABLES.length) return;

  const popup = document.createElement('div');
  popup.className = 'var-autocomplete';
  popup.hidden = true;
  document.body.appendChild(popup);

  let state = null; // { el, start, end, matches, active }

  function isEligible(el) {
    if (!(el instanceof HTMLInputElement) && !(el instanceof HTMLTextAreaElement)) return false;
    if (el instanceof HTMLInputElement && el.type !== 'text') return false;
    if (el.closest('.clr-field')) return false; // Coloris hex input
    if (el.classList.contains('no-var-autocomplete')) return false;
    if (el.dataset.chipUpgraded) return false; // handled by variable-chips.js instead
    return true;
  }

  function closePopup() {
    popup.hidden = true;
    state = null;
  }

  function renderPopup() {
    popup.innerHTML = '';
    state.matches.forEach((v, i) => {
      const item = document.createElement('div');
      item.className = 'var-autocomplete-item' + (i === state.active ? ' active' : '');
      item.innerHTML = `<div class="var-tag">${v.tag}</div><div class="var-desc">${v.desc}</div>`;
      item.addEventListener('mousedown', (e) => e.preventDefault()); // keep focus on field
      item.addEventListener('click', () => selectVariable(v));
      popup.appendChild(item);
    });

    const scrolled = popup.querySelector('.active');
    if (scrolled) scrolled.scrollIntoView({ block: 'nearest' });
  }

  function positionPopup(el) {
    const rect = el.getBoundingClientRect();
    const top = rect.bottom + window.scrollY + 4;
    const left = rect.left + window.scrollX;
    popup.style.top = `${top}px`;
    popup.style.left = `${left}px`;
    popup.style.minWidth = `${Math.min(Math.max(rect.width, 240), 340)}px`;
  }

  function selectVariable(v) {
    if (!state) return;
    const { el, start, end } = state;
    const value = el.value;
    const newValue = value.slice(0, start) + v.tag + value.slice(end);
    el.value = newValue;
    const cursor = start + v.tag.length;
    el.setSelectionRange(cursor, cursor);
    el.focus();
    el.dispatchEvent(new Event('input', { bubbles: true }));
    closePopup();
  }

  function handleInput(e) {
    const el = e.target;
    if (!isEligible(el)) return;

    const pos = el.selectionStart;
    const beforeCursor = el.value.slice(0, pos);
    const braceIndex = beforeCursor.lastIndexOf('{');

    if (braceIndex === -1) return closePopup();

    const query = beforeCursor.slice(braceIndex + 1);
    if (/[\s{}]/.test(query)) return closePopup();

    const matches = VARIABLES.filter((v) =>
      v.tag.slice(1, -1).toLowerCase().includes(query.toLowerCase())
    );
    if (!matches.length) return closePopup();

    state = { el, start: braceIndex, end: pos, matches, active: 0 };
    positionPopup(el);
    renderPopup();
    popup.hidden = false;
  }

  function handleKeydown(e) {
    if (!state || popup.hidden || state.el !== e.target) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      state.active = (state.active + 1) % state.matches.length;
      renderPopup();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      state.active = (state.active - 1 + state.matches.length) % state.matches.length;
      renderPopup();
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      selectVariable(state.matches[state.active]);
    } else if (e.key === 'Escape') {
      closePopup();
    }
  }

  document.addEventListener('input', handleInput, true);
  document.addEventListener('keydown', handleKeydown, true);
  document.addEventListener('scroll', (e) => {
    if (state && e.target.contains && e.target.contains(state.el)) positionPopup(state.el);
  }, true);
  document.addEventListener('blur', (e) => {
    if (state && e.target === state.el) setTimeout(closePopup, 100);
  }, true);
  window.addEventListener('resize', closePopup);
})();
