let toastWrapper, toast;
let update_data = {};

// key -> function(savedVal) that restores that field's DOM to its saved state.
// Keys present in `update_data` but missing here can't be reverted in-place, so
// btn_cancel() falls back to a full reload when any such key is pending.
const _reverts = {};
// key -> value as it was at page load (or after the last successful save).
const _baseline = {};

function show_toast(key, oldVal, val, revert) {
  toastWrapper = document.getElementById('save_toast')
  toast = new bootstrap.Toast(toastWrapper)

  // Call sites pass the page-load value as `oldVal`, but after a save the
  // saved value moves on (btn_save advances _baseline). Diff against the live
  // baseline when we have one so re-editing after a save is still detected.
  let base = (key in _baseline) ? _baseline[key] : oldVal;

  if (base === "True" || base === "False") {
    base = base.toLowerCase() == "true" ? true : false
  }

  // Arrays/objects (e.g. embed fields) are never === / == equal by value in
  // JS even when their contents match, so a plain != always looks "changed".
  // Fall back to a deep compare for those; primitives keep the old behavior.
  const changed = (base !== null && typeof base === "object") ||
                  (val !== null && typeof val === "object")
    ? JSON.stringify(base) !== JSON.stringify(val)
    : base != val;

  if (changed) {
    if (!(key in _baseline)) _baseline[key] = base;
    update_data[key] = val
    if (typeof revert === 'function') _reverts[key] = revert;
    toast.show()
  } else {
    delete update_data[key]
    delete _reverts[key]
  }

  if (Object.keys(update_data).length == 0) {
    toast.hide()
  }
}

// discard pending edits and restore the last-saved state
function btn_cancel() {
  const pending = Object.keys(update_data);
  const unrevertable = pending.some((key) => typeof _reverts[key] !== 'function');

  if (unrevertable) {
    update_data = {}
    if (toast) toast.hide()
    window.location.reload()
    return;
  }

  pending.forEach((key) => _reverts[key](_baseline[key]));
  update_data = {}
  for (const k in _reverts) delete _reverts[k];
  if (toast) toast.hide()
}

// get the save button
function btn_save(guild_id) {
  console.log(update_data)
  fetch(`/dashboard/${guild_id}/data/post`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(update_data),
  })
    .then(response => response.json())
    .then(data => {
      if (data.status == 'success') {
        toastWrapper.style.backgroundColor = "#3ba55d"

        // Saved values become the new baseline so re-editing back to them
        // correctly reads as "no change".
        Object.keys(update_data).forEach((key) => { _baseline[key] = update_data[key] });

        setTimeout(() => {
          toastWrapper.classList.remove('show');
          toastWrapper.removeAttribute("style")
        }, 500)
      } else {
        toastWrapper.style.backgroundColor = "#f23f43"
        console.error(data?.message)
      }

      update_data = {}
      for (const k in _reverts) delete _reverts[k];
    })
}
