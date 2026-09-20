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
 * as they appear. Variable list comes from variables-data.js
 * (window.BOT_VARIABLES), shared with variable-autocomplete.js — works on
 * every dashboard page unconditionally, no per-page opt-in needed.
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
  const VARIABLES = window.BOT_VARIABLES || [];
  if (!VARIABLES.length) return;

  const byTagLower = new Map(VARIABLES.map((v) => [v.tag.toLowerCase(), v]));

  // A zero-width space used as a stable caret anchor inside an otherwise-
  // empty pending span (see wrapPending). Browsers routinely normalize a
  // genuinely empty text node away the instant typing starts, silently
  // kicking the caret out to the wrong place — the ZWSP keeps the node
  // "real" without being visible. Stripped everywhere real text is read.
  const ZWSP = '\u200B';
  const stripZWSP = (s) => s.split(ZWSP).join('');

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
    return stripZWSP(out);
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
    // Opt-out for fields where `{variable}` tags are just literal user
    // content, not template placeholders - e.g. a form respondent's answer
    // on the public form-fill page (web_dashboard/templates/dashboard/
    // plugins/forms/form.html).
    if (original.classList.contains('no-var-chips')) return;
    // Disabled/readonly fields are static examples (e.g. the giveaway
    // message preview's title/desc, which reuse the .embed wrapper classes
    // purely for styling) - never meant to be interactive, so leave them as
    // plain text instead of swapping in the editable chip UI.
    if (original.disabled || original.readOnly) return;
    original.dataset.chipUpgraded = '1';

    const multiline = original.tagName === 'TEXTAREA';

    const root = document.createElement('div');
    root.className = original.className;
    root.classList.add('rich-var-field');
    if (original.tagName === 'TEXTAREA') root.classList.add('rich-var-field--multiline');
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
        else text += node.textContent; // covers a partially-cloned .var-chip-pending
      });
      return stripZWSP(text);
    }

    // While `{query` is a live, still-editable trigger, wrap it in a
    // `.var-chip-pending` span so it's highlighted the instant `{` is typed
    // — not just once a variable is picked. Only one can be open per field.
    // The `{` itself is a real (but visually hidden) child span, so the
    // pending highlight reads as just the typed name, no visible braces.
    let pendingSpan = null;

    function wrapPending() {
      const sel = window.getSelection();
      if (!sel.rangeCount) return;
      const range = sel.getRangeAt(0);
      const node = range.startContainer;
      if (node.nodeType !== Node.TEXT_NODE) return;

      const offset = range.startOffset;
      const nodeText = node.nodeValue;
      const braceIndex = nodeText.lastIndexOf('{', offset - 1);
      if (braceIndex === -1) return;

      const before = nodeText.slice(0, braceIndex);
      const query = nodeText.slice(braceIndex + 1, offset);
      const after = nodeText.slice(offset);

      const span = document.createElement('span');
      span.className = 'var-chip-pending';

      const brace = document.createElement('span');
      brace.className = 'var-chip-brace';
      brace.contentEditable = 'false';
      brace.textContent = '{';
      span.appendChild(brace);

      // The query text node always gets at least a ZWSP so it's never
      // genuinely empty — an empty text node is unstable in contenteditable
      // (browsers routinely normalize/drop it right as typing starts),
      // which silently kicks the caret out to the wrong spot entirely.
      const queryNode = document.createTextNode(query.length > 0 ? query : ZWSP);
      span.appendChild(queryNode);

      const parent = node.parentNode;
      const afterNode = document.createTextNode(after);
      parent.replaceChild(afterNode, node);
      parent.insertBefore(span, afterNode);
      if (before) parent.insertBefore(document.createTextNode(before), span);

      const newRange = document.createRange();
      newRange.setStart(queryNode, queryNode.length);
      newRange.collapse(true);
      sel.removeAllRanges();
      sel.addRange(newRange);

      pendingSpan = span;
    }

    // Collapses the pending span back to a plain text node (trigger became
    // invalid, or a variable is about to be inserted in its place) and
    // returns that node so callers can keep working with it.
    function flattenPending() {
      if (!pendingSpan) return null;
      const textNode = document.createTextNode(stripZWSP(pendingSpan.textContent));
      if (pendingSpan.parentNode) pendingSpan.parentNode.replaceChild(textNode, pendingSpan);
      pendingSpan = null;
      return textNode;
    }

    function caretInsidePending() {
      if (!pendingSpan) return false;
      const sel = window.getSelection();
      if (!sel.rangeCount) return false;
      return pendingSpan.contains(sel.getRangeAt(0).startContainer);
    }

    function handleTrigger() {
      // The caret can leave a pending span without ever "finishing" it —
      // click elsewhere and keep typing, tab away and back, etc. Clean up
      // the abandoned span in place (never touching the *current*
      // selection) before evaluating the caret's own trigger state, or
      // typing somewhere else would keep flattening + reclaiming the
      // caret back to the old spot, scrambling whatever was just typed.
      if (pendingSpan && !caretInsidePending()) {
        const stale = pendingSpan;
        pendingSpan = null;
        const textNode = document.createTextNode(stripZWSP(stale.textContent));
        if (stale.parentNode) stale.parentNode.replaceChild(textNode, stale);
      }

      const text = getCaretTextBefore();
      if (text == null) return closePopup();
      const braceIndex = text.lastIndexOf('{');

      if (braceIndex === -1) {
        if (pendingSpan) {
          const node = flattenPending();
          placeCaretAtEnd(node);
        }
        return closePopup();
      }

      const query = text.slice(braceIndex + 1);
      if (/[\s{}]/.test(query)) {
        // Typing (or pasting) `}` completes a manually-written tag — if it
        // matches a known variable, promote it straight to a real chip
        // instead of just flattening it back to plain text. A paste lands
        // as one batched insertion with no pendingSpan built up yet, so
        // wrap it retroactively before checking.
        if (query.endsWith('}') && !/[\s{]/.test(query.slice(0, -1))) {
          if (!pendingSpan) wrapPending();
        }
        if (pendingSpan && query.endsWith('}') && !/[\s{]/.test(query.slice(0, -1))) {
          const known = byTagLower.get(stripZWSP(pendingSpan.textContent).toLowerCase());
          if (known) {
            const chip = makeChip(known.tag);
            pendingSpan.parentNode.replaceChild(chip, pendingSpan);
            pendingSpan = null;
            const sel = window.getSelection();
            const r = document.createRange();
            r.setStartAfter(chip);
            r.collapse(true);
            sel.removeAllRanges();
            sel.addRange(r);
            syncToOriginal();
            return closePopup();
          }
        }
        if (pendingSpan) {
          const node = flattenPending();
          placeCaretAtEnd(node);
        }
        return closePopup();
      }

      // Wrap immediately, even before anything's typed after `{` — the
      // empty pending pill gets a deliberate min-width in CSS so it reads
      // as a small marker chip, not a stray sliver.
      if (!pendingSpan) wrapPending();

      const matches = VARIABLES.filter((v) =>
        v.tag.slice(1, -1).toLowerCase().includes(query.toLowerCase())
      );
      if (!matches.length) return closePopup();

      state = { root, matches, active: 0 };
      positionPopup(root);
      renderPopup();
      popup.hidden = false;
    }

    function placeCaretAtEnd(node) {
      if (!node) return;
      const sel = window.getSelection();
      const range = document.createRange();
      range.setStart(node, node.length != null ? node.length : 0);
      range.collapse(true);
      sel.removeAllRanges();
      sel.addRange(range);
    }

    root.addEventListener('input', () => {
      syncToOriginal();
      handleTrigger();
    });

    // Pasting inserts rich clipboard content (HTML) by default, not plain
    // text, and can land anywhere in a bigger block of text — a completed
    // `{tag}` might end up nowhere near the caret once the rest of the
    // paste lands after it. So build the fragment ourselves: split the
    // pasted text on every complete `{tag}`, convert known ones to real
    // chips inline, and insert that instead of relying on the caret-
    // adjacent trigger heuristic used for normal typing.
    root.addEventListener('paste', (e) => {
      e.preventDefault();
      const text = (e.clipboardData || window.clipboardData).getData('text/plain');
      if (!text) return;

      const sel = window.getSelection();
      if (!sel.rangeCount) return;
      const range = sel.getRangeAt(0);
      range.deleteContents();

      const frag = document.createDocumentFragment();
      const regex = /\{[^{}]+\}/g;
      let lastIndex = 0;
      let m;
      let tailNode = null;
      while ((m = regex.exec(text))) {
        appendTextWithBreaks(frag, text.slice(lastIndex, m.index));
        const known = byTagLower.get(m[0].toLowerCase());
        tailNode = known ? makeChip(known.tag) : document.createTextNode(m[0]);
        frag.appendChild(tailNode);
        lastIndex = m.index + m[0].length;
      }
      appendTextWithBreaks(frag, text.slice(lastIndex));
      if (!frag.lastChild) frag.appendChild(document.createTextNode(''));
      tailNode = frag.lastChild;

      range.insertNode(frag);
      const newRange = document.createRange();
      // A trailing chip is atomic — the caret sits after it as a sibling
      // boundary. Trailing plain text needs the caret genuinely *inside*
      // that text node, or wrapPending()'s TEXT_NODE check (run right after
      // via handleTrigger()) sees an element boundary and silently no-ops —
      // so a paste ending mid-trigger (e.g. "hello {ser") never highlights.
      if (tailNode.nodeType === Node.TEXT_NODE) {
        newRange.setStart(tailNode, tailNode.length);
      } else {
        newRange.setStartAfter(tailNode);
      }
      newRange.collapse(true);
      sel.removeAllRanges();
      sel.addRange(newRange);

      syncToOriginal();
      handleTrigger(); // paste can still end mid-trigger, e.g. "hello {ser"
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

    root.addEventListener('blur', () => {
      setTimeout(() => {
        // Only tidy up if focus didn't move into our own popup (a click
        // there blurs the field for a tick before selectVariable runs).
        if (popup.hidden) flattenPending();
        closePopup();
      }, 100);
    });

    // exposed for selectVariable()
    root._syncToOriginal = syncToOriginal;
    root._flattenPending = flattenPending;
  }

  function selectVariable(v) {
    if (!state) return;
    const { root } = state;
    const sel = window.getSelection();

    // Collapse the live pending highlight back to a plain text node first —
    // it's a normal editable span, not the raw text node the swap below
    // expects, and the caret sits at its end either way.
    const flat = root._flattenPending();
    let node, offset;
    if (flat) {
      node = flat;
      offset = flat.length;
    } else {
      const range = sel.getRangeAt(0);
      node = range.startContainer;
      offset = range.startOffset;
    }

    if (node.nodeType === Node.TEXT_NODE) {
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
