
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
  var currentURL = window.location.pathname;
  var link = event.currentTarget;
  
  // p_fae9dd is premium - p_a2b8c9 is not premium
  const aClassPrem = link.classList.contains('p_fae9dd') // is the plugin premium

  const isPremium = link.dataset.isPremium // server check - True if hasPrem else False

  if (aClassPrem === true && isPremium === 'False') {
    const PremiumModal = new bootstrap.Modal(document.getElementById('PremiumModal'));
    PremiumModal.show();
  } else {
    var url = link.dataset.href;
    var isActive = url === currentURL;
    event.target.dataset.active = isActive ? "True" : "False";

    document.location.href = url;
  }
}

try {
  var Switch = document.querySelector("input[role='switch'][name='plugin-status']")
  if (Switch) {
    Switch.addEventListener('change', (e) => {
      const currentURL = window.location.pathname;
      const URL = currentURL.split('/')
      var PlugIn = URL[URL.length - 1]
      
      const navBarLink = document.querySelector(`.navbar-link.${PlugIn}`);
      const dataHref = navBarLink.getAttribute('data-href');
      if (window.location.pathname === dataHref) {
        navBarLink.setAttribute('data-enable', e.target.checked ? 'True' : 'False');
      }
    })
  }
} catch (error) {}