/**
 * Shared wiring for components/embed_editor.html `embed_editor()` instances.
 *
 * Handles Coloris init, per-field `input` listeners, and dynamic field
 * management (add/remove fields with inline toggle).
 */

function autoGrowEmbedDesc(el) {
  el.style.height = "5px";
  el.style.height = (el.scrollHeight + 2) + "px";
}

function initEmbedEditor(instances) {
  // Store instances globally for field operations
  window._embedInstances = instances;

  // Color picker  
  Coloris({
    el: '.coloris-embed-color',
    theme: 'large',
    themeMode: 'dark',
    format: 'hex',
    formatToggle: false,
    closeButton: true,
    defaultColor: '#5865f2',
    swatches: ['#5865f2', '#57F287', '#FEE75C', '#EB459E', '#ED4245', '#FFFFFF', '#000000']
  });

  instances.forEach(({ prefix, colorId, dataKeyPrefix, initial, fieldDataKeyPrefix }) => {
    const bind = (id, key, initialVal) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener('input', (e) => {
        show_toast(key, initialVal, e.target.value, () => { el.value = initialVal == null ? '' : initialVal; });
      });
    };

    bind(`${prefix}-author`, `${dataKeyPrefix}.author.name`, initial.author);
    bind(`${prefix}-title`, `${dataKeyPrefix}.title`, initial.title);
    bind(`${prefix}-desc`, `${dataKeyPrefix}.description`, initial.desc);
    bind(`${prefix}-footer`, `${dataKeyPrefix}.footer.text`, initial.footer);

    // Color picker
    const colorEl = document.getElementById(colorId);
    if (colorEl) {
      colorEl.dataset.prefix = prefix;
      colorEl.dataset.key = `${dataKeyPrefix}.color`;
      colorEl.dataset.initial = initial.color;
    }

    // Initialize fields
    const fieldsContainer = document.getElementById(`${prefix}-fields`);
    if (fieldsContainer) {
      // Store the field data key prefix (defaults to dataKeyPrefix if not specified)
      const fieldKeyPrefix = fieldDataKeyPrefix || dataKeyPrefix;

      // Baseline for the "old value" show_toast compares against — captured
      // once from server-rendered data, same as every other field on this
      // page (color/author/title/desc/footer all diff against their
      // page-load value, not their value one keystroke ago).
      //
      // Templates pass `fields` as a Jinja tojson string (kept quoted so
      // editors don't flag a bare `{{ }}` as invalid JS) rather than a raw
      // array literal, so accept either shape here.
      const initialFields = typeof initial.fields === 'string'
        ? JSON.parse(initial.fields || '[]')
        : (initial.fields || []);
      fieldsContainer.dataset.initialFields = JSON.stringify(initialFields);

      // Set up field listeners for existing fields
      setupFieldListeners(prefix, fieldKeyPrefix, fieldsContainer);
      
      // Add field button
      const addBtn = document.querySelector(`.add-field-btn[data-prefix="${prefix}"]`);
      if (addBtn) {
        addBtn.addEventListener('click', () => addField(prefix, fieldKeyPrefix));
      }
    }
  });

  // Coloris pick event
  document.addEventListener('coloris:pick', (event) => {
    const input = event.target;
    if (!input || !input.classList || !input.classList.contains('coloris-embed-color')) return;

    const { prefix, key, initial } = input.dataset;
    const embedEl = document.querySelector(`.embed[data-prefix="${prefix}"]`);
    if (embedEl) embedEl.style.borderLeftColor = event.detail.color;

    show_toast(key, initial, event.detail.color, () => {
      input.value = initial == null ? '' : initial;
      if (embedEl) embedEl.style.borderLeftColor = initial;
    });
  });
}

function setupFieldListeners(prefix, dataKeyPrefix, container) {
  // Name inputs
  container.querySelectorAll('.field-name-input').forEach(input => {
    input.removeEventListener('input', handleFieldNameChange);
    input.addEventListener('input', handleFieldNameChange);
    input.dataset.fieldKeyPrefix = dataKeyPrefix;
  });

  // Value inputs
  container.querySelectorAll('.field-value-input').forEach(input => {
    input.removeEventListener('input', handleFieldValueChange);
    input.addEventListener('input', handleFieldValueChange);
    input.dataset.fieldKeyPrefix = dataKeyPrefix;
  });

  // Inline checkboxes
  container.querySelectorAll('.field-inline-checkbox').forEach(checkbox => {
    checkbox.removeEventListener('change', handleFieldInlineChange);
    checkbox.addEventListener('change', handleFieldInlineChange);
    checkbox.dataset.fieldKeyPrefix = dataKeyPrefix;
  });

  // Remove buttons
  container.querySelectorAll('.remove-field-btn').forEach(btn => {
    btn.removeEventListener('click', handleFieldRemove);
    btn.addEventListener('click', handleFieldRemove);
    btn.dataset.fieldKeyPrefix = dataKeyPrefix;
  });
}


function handleFieldNameChange(e) {
  const input = e.target;
  const dataKeyPrefix = input.dataset.fieldKeyPrefix;
  const container = input.closest('.fields');

  if (!container) return;

  saveFieldsArray(container, dataKeyPrefix);
}

function handleFieldValueChange(e) {
  const input = e.target;
  const dataKeyPrefix = input.dataset.fieldKeyPrefix;

  const container = input.closest('.fields');
  if (!container) return;
  saveFieldsArray(container, dataKeyPrefix);
}

function handleFieldInlineChange(e) {
  const checkbox = e.target;
  const dataKeyPrefix = checkbox.dataset.fieldKeyPrefix;

  const fieldWrapper = checkbox.closest('.field-wrapper');
  const fieldDiv = fieldWrapper.querySelector('.field');

  if (checkbox.checked) {
    fieldDiv.classList.add('inline');
  } else {
    fieldDiv.classList.remove('inline');
  }

  const container = checkbox.closest('.fields');
  if (!container) return;
  saveFieldsArray(container, dataKeyPrefix);
}


function getFieldsData(container) {
  return Array.from(container.querySelectorAll('.field-wrapper')).map(wrapper => {
    const nameInput = wrapper.querySelector('.field-name-input');
    const valueInput = wrapper.querySelector('.field-value-input');
    const inlineInput = wrapper.querySelector('.field-inline-checkbox');

    return {
      name: nameInput?.value || '',
      value: valueInput?.value || '',
      inline: inlineInput?.checked || false
    };
  });
}

function normalizeField(field) {
  // DB-sourced field dicts don't always carry every key (e.g. a field saved
  // before "inline" was tracked, or a hand-written one). getFieldsData()
  // always yields the full {name, value, inline} shape, so the baseline
  // needs the same normalization or an untouched field never compares equal
  // to itself and the "unsaved changes" toast can never clear.
  return {
    name: field?.name || '',
    value: field?.value || '',
    inline: !!field?.inline
  };
}

function saveFieldsArray(container, dataKeyPrefix) {
  const newFields = getFieldsData(container);
  const oldFields = container.dataset.initialFields || '[]';

  const oldFieldsJson = JSON.parse(oldFields).map(normalizeField);
  const prefix = container.id.replace(/-fields$/, '');

  show_toast(
    `${dataKeyPrefix}.fields`,
    oldFieldsJson,
    newFields,
    () => renderFields(prefix, dataKeyPrefix, oldFieldsJson)
  );
}

function handleFieldRemove(e) {
  const btn = e.currentTarget;
  const dataKeyPrefix = btn.dataset.fieldKeyPrefix;
  const fieldWrapper = btn.closest('.field-wrapper');
  const container = fieldWrapper.parentElement;

  if (!container) return;

  // Remove the field from the DOM.
  fieldWrapper.remove();

  // Re-index every remaining field.
  container.querySelectorAll('.field-wrapper').forEach((wrapper, newIndex) => {
    wrapper.dataset.index = newIndex;

    wrapper.querySelectorAll('input').forEach(input => {
      input.dataset.index = newIndex;
    });

    wrapper.querySelectorAll(
      '.remove-field-btn, .field-inline-checkbox'
    ).forEach(el => {
      el.dataset.index = newIndex;
    });
  });

  // Save the complete fields array.
  saveFieldsArray(container, dataKeyPrefix);
}


function fieldWrapperHTML(prefix, dataKeyPrefix, index) {
  return `
    <div class="field">
      <div class="field-header d-flex justify-content-between align-items-center">
        <div class="name">
          <input
            type="text"
            class="field-name-input"
            placeholder="Field name"
            data-prefix="${prefix}"
            data-index="${index}"
            data-field-key-prefix="${dataKeyPrefix}">
        </div>

        <button
          type="button"
          class="btn btn-danger btn-sm remove-field-btn"
          data-prefix="${prefix}"
          data-index="${index}"
          data-field-key-prefix="${dataKeyPrefix}">
          <i class="bi bi-x"></i>
        </button>
      </div>

      <div class="value">
        <input
          type="text"
          class="field-value-input"
          placeholder="Field value"
          data-prefix="${prefix}"
          data-index="${index}"
          data-field-key-prefix="${dataKeyPrefix}">
      </div>

      <div class="field-options">
        <input
          type="checkbox"
          class="field-inline-checkbox"
          style="margin-right: 5px; width: 16px; height: 16px;"
          id="${prefix}-field-${index}-inline-checkbox"
          data-prefix="${prefix}"
          data-index="${index}"
          data-field-key-prefix="${dataKeyPrefix}">

        <label for="${prefix}-field-${index}-inline-checkbox">
          Inline
        </label>
      </div>
    </div>
  `;
}

// Rebuild a fields container from a plain [{name, value, inline}] array.
// Used both for adding one field and for reverting to the saved state.
function renderFields(prefix, dataKeyPrefix, fields) {
  const container = document.getElementById(`${prefix}-fields`);
  if (!container) return null;

  container.innerHTML = '';
  fields.forEach((field, index) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'field-wrapper';
    wrapper.dataset.index = index;
    wrapper.innerHTML = fieldWrapperHTML(prefix, dataKeyPrefix, index);
    wrapper.querySelector('.field-name-input').value = field?.name || '';
    wrapper.querySelector('.field-value-input').value = field?.value || '';
    wrapper.querySelector('.field-inline-checkbox').checked = !!field?.inline;
    container.appendChild(wrapper);
  });

  setupFieldListeners(prefix, dataKeyPrefix, container);
  return container;
}

function addField(prefix, dataKeyPrefix) {
  const container = document.getElementById(`${prefix}-fields`);
  if (!container) return;

  const newIndex = getFieldsData(container).length;

  const wrapper = document.createElement('div');
  wrapper.className = 'field-wrapper';
  wrapper.dataset.index = newIndex;
  wrapper.innerHTML = fieldWrapperHTML(prefix, dataKeyPrefix, newIndex);

  container.appendChild(wrapper);

  // Rebind listeners.
  setupFieldListeners(prefix, dataKeyPrefix, container);

  // Save the complete array.
  saveFieldsArray(container, dataKeyPrefix);

  // Focus the new field.
  const nameInput = wrapper.querySelector('.field-name-input');

  if (nameInput) {
    setTimeout(() => nameInput.focus(), 50);
  }
}