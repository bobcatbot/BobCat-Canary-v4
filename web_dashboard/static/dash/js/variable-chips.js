/**
 * Renders inserted `{variable}` tags as pill/chip tokens (like a Discord
 * mention) inside the plain-text message boxes, instead of leaving them as
 * raw curly-brace text.
 *
 * Scope: `textarea.text-input` message boxes (join/dm/leave welcome
 * messages, level-up announcement, birthday message, etc.) plus every field
 * inside a Discord embed editor — author/title/description/footer and the
 * field name/value inputs (components/embed_editor.html). Embed fields are
 * dynamically added ("Add Field"), so a MutationObserver upgrades new ones
 * as they appear.
 *
 * Design: the original <input>/<textarea> is kept in the DOM (hidden) as
 * the single source of truth. A contenteditable "rich" div sits in its
 * place for the user to type into; every edit re-serializes the chip DOM
 * back to plain `{tag}` text and writes it into the original field,
 * dispatching a real `input` event — so every existing script (show_toast
 * diffing, initial content, save/POST payloads, embed-editor.js field
 * wiring) keeps working completely unchanged.
 */
(function () {
  const modal = document.getElementById('VariablesModal');
  if (!modal) return;

  const VARIABLES = Array.from(modal.querySelectorAll('h5')).map((h5) => {
    const desc = h5.nextElementSibling;
    return { tag: h5.textContent.trim(), desc: desc ? desc.textContent.trim() : '' };
  }).filter((v) => v.tag.startsWith('{') && v.tag.endsWith('}'));
  if (!VARIABLES.length) return;

  const byTagLower = new Map(VARIABLES.map((v) => [v.tag.toLowerCase(), v]));

  /* ---------------- shared popup ---------------- */
  const popup = document.createElement('div');
  popup.className = 'var-autocomplete';
  popup.hidden = true;
  document.body.appendChild(popup);

  let state = null; // { root, matches, active }

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
      item.addEventListener('mousedown', (e) => e.preventDefault());
      item.addEventListener('click', () => selectVariable(v));
      popup.appendChild(item);
    });
    const active = popup.querySelector('.active');
    if (active) active.scrollIntoView({ block: 'nearest' });
  }

  function positionPopup(root) {
    const sel = window.getSelection();
    let caretRect = null;
    if (sel.rangeCount) {
      const collapsed = sel.getRangeAt(0).cloneRange();
      collapsed.collapse(true);
      caretRect = collapsed.getClientRects()[0];
    }
    const rect = caretRect || root.getBoundingClientRect();
    popup.style.top = `${rect.bottom + window.scrollY + 4}px`;
    popup.style.left = `${rect.left + window.scrollX}px`;
    popup.style.minWidth = '240px';
  }

  /* ---------------- chip + serialization helpers ---------------- */
  function makeChip(tag) {
    const span = document.createElement('span');
    span.className = 'var-chip';
    span.contentEditable = 'false';
    span.dataset.tag = tag;
    span.textContent = tag.slice(1, -1);
    return span;
  }

  function serialize(root) {
    let out = '';
    root.childNodes.forEach((node) => {
      if (node.nodeType === Node.TEXT_NODE) out += node.nodeValue;
      else if (node.nodeName === 'BR') out += '\n';
      else if (node.classList && node.classList.contains('var-chip')) out += node.dataset.tag;
      else out += node.textContent;
    });
    return out;
  }

  function appendTextWithBreaks(root, text) {
    text.split('\n').forEach((line, i) => {
      if (i > 0) root.appendChild(document.createElement('br'));
      if (line) root.appendChild(document.createTextNode(line));
    });
  }

  function buildContent(root, value) {
    root.innerHTML = '';
    const regex = /\{[^{}]+\}/g;
    let lastIndex = 0;
    let m;
    while ((m = regex.exec(value))) {
      appendTextWithBreaks(root, value.slice(lastIndex, m.index));
      const known = byTagLower.get(m[0].toLowerCase());
      if (known) root.appendChild(makeChip(known.tag));
      else appendTextWithBreaks(root, m[0]);
      lastIndex = m.index + m[0].length;
    }
    appendTextWithBreaks(root, value.slice(lastIndex));
    root.classList.toggle('is-empty', value.length === 0);
  }

  function insertBreakAtCaret() {
    const sel = window.getSelection();
    if (!sel.rangeCount) return;
    const range = sel.getRangeAt(0);
    range.deleteContents();
    const br = document.createElement('br');
    range.insertNode(br);
    range.setStartAfter(br);
    range.collapse(true);
    sel.removeAllRanges();
    sel.addRange(range);
  }

  /* ---------------- upgrade an <input>/<textarea> into a chip editor ---------------- */
  function upgrade(original) {
    if (original.dataset.chipUpgraded) return;
    if (original instanceof HTMLInputElement && original.type !== 'text') return;
    original.dataset.chipUpgraded = '1';

    const multiline = original.tagName === 'TEXTAREA';

    const root = document.createElement('div');
    root.className = original.className;
    root.classList.add('rich-var-field');
    root.contentEditable = 'true';
    root.dataset.placeholder = original.placeholder || '';
    if (original.id) root.id = `${original.id}-rich`;
    // Carry over data-* attributes (embed fields use data-prefix/data-index
    // for click delegation elsewhere) in case anything looks them up on the
    // visible element rather than the hidden original.
    Array.from(original.attributes).forEach((attr) => {
      if (attr.name.startsWith('data-')) root.setAttribute(attr.name, attr.value);
    });
    root._original = original;

    buildContent(root, original.value || '');
    original.style.display = 'none';
    original.insertAdjacentElement('afterend', root);

    // Intercept `.value =` so external resets (e.g. the undo-toast callback
    // that does `el.value = savedContent`) re-render the chip DOM too.
    let internalUpdate = false;
    const valueDesc = Object.getOwnPropertyDescriptor(
      multiline ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype,
      'value'
    );
    Object.defineProperty(original, 'value', {
      configurable: true,
      get() { return valueDesc.get.call(original); },
      set(v) {
        valueDesc.set.call(original, v);
        if (!internalUpdate) buildContent(root, v);
      },
    });

    function syncToOriginal() {
      const serialized = serialize(root);
      if (valueDesc.get.call(original) === serialized) return;
      internalUpdate = true;
      original.value = serialized;
      internalUpdate = false;
      original.dispatchEvent(new Event('input', { bubbles: true }));
      root.classList.toggle('is-empty', serialized.length === 0);
    }

    function getCaretTextBefore() {
      const sel = window.getSelection();
      if (!sel.rangeCount) return null;
      const range = sel.getRangeAt(0);
      if (!root.contains(range.startContainer)) return null;
      const preRange = document.createRange();
      preRange.selectNodeContents(root);
      preRange.setEnd(range.startContainer, range.startOffset);
      const frag = preRange.cloneContents();
      let text = '';
      frag.childNodes.forEach((node) => {
        if (node.nodeType === Node.TEXT_NODE) text += node.nodeValue;
        else if (node.nodeName === 'BR') text += '\n';
        else if (node.classList && node.classList.contains('var-chip')) text += node.dataset.tag;
      });
      return text;
    }

    function handleTrigger() {
      const text = getCaretTextBefore();
      if (text == null) return closePopup();
      const braceIndex = text.lastIndexOf('{');
      if (braceIndex === -1) return closePopup();
      const query = text.slice(braceIndex + 1);
      if (/[\s{}]/.test(query)) return closePopup();

      const matches = VARIABLES.filter((v) =>
        v.tag.slice(1, -1).toLowerCase().includes(query.toLowerCase())
      );
      if (!matches.length) return closePopup();

      state = { root, matches, active: 0 };
      positionPopup(root);
      renderPopup();
      popup.hidden = false;
    }

    root.addEventListener('input', () => {
      syncToOriginal();
      handleTrigger();
    });

    root.addEventListener('keydown', (e) => {
      if (state && !popup.hidden && state.root === root) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          state.active = (state.active + 1) % state.matches.length;
          renderPopup();
          return;
        }
        if (e.key === 'ArrowUp') {
          e.preventDefault();
          state.active = (state.active - 1 + state.matches.length) % state.matches.length;
          renderPopup();
          return;
        }
        if (e.key === 'Enter' || e.key === 'Tab') {
          e.preventDefault();
          selectVariable(state.matches[state.active]);
          return;
        }
        if (e.key === 'Escape') {
          closePopup();
          return;
        }
      }
      if (e.key === 'Enter') {
        e.preventDefault(); // never a literal newline in a single-line field
        if (multiline) {
          insertBreakAtCaret();
          syncToOriginal();
        }
      }
    });

    root.addEventListener('blur', () => setTimeout(closePopup, 100));

    // exposed for selectVariable()
    root._syncToOriginal = syncToOriginal;
  }

  function selectVariable(v) {
    if (!state) return;
    const { root } = state;
    const sel = window.getSelection();
    const range = sel.getRangeAt(0);
    const node = range.startContainer;

    if (node.nodeType === Node.TEXT_NODE) {
      const offset = range.startOffset;
      const nodeText = node.nodeValue;
      const braceIndex = nodeText.lastIndexOf('{', offset - 1);
      if (braceIndex !== -1) {
        const before = nodeText.slice(0, braceIndex);
        const after = nodeText.slice(offset);
        const chip = makeChip(v.tag);
        const afterNode = document.createTextNode(after);
        const parent = node.parentNode;
        parent.replaceChild(afterNode, node);
        parent.insertBefore(chip, afterNode);
        if (before) parent.insertBefore(document.createTextNode(before), chip);

        const newRange = document.createRange();
        newRange.setStart(afterNode, 0);
        newRange.collapse(true);
        sel.removeAllRanges();
        sel.addRange(newRange);
      }
    }

    root._syncToOriginal();
    closePopup();
    root.focus();
  }

  const SELECTOR = [
    'textarea.text-input',
    '.embed input[type="text"]',
    '.embed textarea',
    '.field-name-input',
    '.field-value-input',
  ].join(', ');

  document.querySelectorAll(SELECTOR).forEach(upgrade);

  // Embed fields can be added later ("Add Field" button) — upgrade those too.
  new MutationObserver((mutations) => {
    mutations.forEach((m) => {
      m.addedNodes.forEach((node) => {
        if (node.nodeType !== Node.ELEMENT_NODE) return;
        if (node.matches(SELECTOR)) upgrade(node);
        node.querySelectorAll && node.querySelectorAll(SELECTOR).forEach(upgrade);
      });
    });
  }).observe(document.body, { childList: true, subtree: true });
})();
