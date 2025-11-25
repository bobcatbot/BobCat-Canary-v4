
const toastBS = document.getElementById('ToastBS')
const title = document.getElementById('cate')
if (toastBS) {
  if (title.innerText.includes("-")) {
    var new_title = title.innerText.replace("-", " ")
    title.innerText = new_title
  }
  
  const toast = new bootstrap.Toast(toastBS)
  toast.show()
  setTimeout(() => {
    toast.hide()
  }, 8000)
}