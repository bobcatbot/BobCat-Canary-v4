let toastWrapper, toast;
let update_data = {};

function show_toast(key, oldVal, val) {
  toastWrapper = document.getElementById('save_toast')
  toast = new bootstrap.Toast(toastWrapper)

  if (oldVal === "True" || oldVal === "False") {
    oldVal = oldVal.toLowerCase() == "true" ? true : false
  }
  
  if (oldVal != val) {
    update_data[key] = val
    toast.show()
  } else {
    delete update_data[key]
  }

  if (Object.keys(update_data).length == 0) {
    toast.hide()
  }
  
  // update_data = save_data
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

        setTimeout(() => {
          toastWrapper.classList.remove('show');
          toastWrapper.removeAttribute("style")
        }, 500)
      } else {
        toastWrapper.style.backgroundColor = "#f23f43"
        console.error(data?.message)
      }

      delete save_data
      delete update_data
    })
}