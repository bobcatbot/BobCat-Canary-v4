
(function() {
  "use strict";

  console.log(
    "%cWait",
    `color: #5865F2;
    font-size: 56px;
    `
  );
  console.log(
    `%cUnless you understand exactly what you are doing, close this window and stay safe.`,
    `font-size: 20px;`
  );
  console.log(
    `%cIf you do understand exactly what you are doing, you should come work with us https://www.bobcatbot.xyz/jobs/`,
    `font-size: 20px;`
  );

  console.log(
    `Vote For BobCat https://top.gg/bot/961762686671155240`
  );

  /* Changelog modal */
  try {
    var changeLogDate = localStorage.getItem('lastChangeLogDate')
    var showChangeLog = localStorage.getItem('showChangeLog')
    var modal = new bootstrap.Modal(document.getElementById('changelogModal'))
  
    document.addEventListener('DOMContentLoaded', function () {
      var request = new XMLHttpRequest()
      request.onreadystatechange = function () {
        if (this.readyState == 4 && this.status == 200) {
          var data = JSON.parse(this.responseText)
  
          document.getElementById('modalTitle').textContent = "Changelog - v" + data.version
          document.getElementById('modalTitleDate').textContent = data.date
          document.getElementById('modalbody-info').textContent = data.description
  
          data.added.forEach((item) => {
            var add = document.createElement('li')
            add.innerHTML = `<b>${item.title}</b>. ${item.description}`
            document.getElementById('added-list').appendChild(add)
          })
  
          data.updates.forEach((item) => {
            var remove = document.createElement('li')
            remove.innerHTML = `<b>${item.title}</b>. ${item.description}`
            document.getElementById('updates-list').appendChild(remove)
          })
  
          data.bugs.forEach((item) => {
            var update = document.createElement('li')
            update.innerHTML = `<b>${item.title}</b>. ${item.description}`
            document.getElementById('bugs-list').appendChild(update)
          })

          // if (changeLogDate !== data.short_date) {
          //   localStorage.setItem('lastChangeLogDate', data.short_date)
          //   localStorage.setItem('showChangeLog', true)
          //   modal.show()
          // }
      
          // if (changeLogDate !== data.short_date && showChangeLog === true) {
          //   localStorage.setItem('showChangeLog', false)
          //   modal.show()
          // } else {
          //   localStorage.setItem('showChangeLog', true)
          //   modal.hide()
          // }
        }
      }
      request.open('GET', "/static/changelog.json", true)
      request.send()
    })
    
    document.getElementById('changelogModal').addEventListener('hidden.bs.modal', (e) => {
      localStorage.setItem('lastChangeLogDate', date)
      localStorage.setItem('showChangeLog', false)
    })
  } catch (error) {
  }
  /* end of changelog */
  
  /**
   * Easy selector helper function
   */
  const select = (el, all = false) => {
    el = el.trim()
    if (all) {
      return [...document.querySelectorAll(el)]
    } else {
      return document.querySelector(el)
    }
  }

  /**
   * Easy event listener function
   */
  const on = (type, el, listener, all = false) => {
    let selectEl = select(el, all)
    if (selectEl) {
      if (all) {
        selectEl.forEach(e => e.addEventListener(type, listener))
      } else {
        selectEl.addEventListener(type, listener)
      }
    }
  }

  /**
   * Easy on scroll event listener 
   */
  const onscroll = (el, listener) => {
    el.addEventListener('scroll', listener)
  }

  /**
   * Navbar links active state on scroll
   */
  let navbarlinks = select('#navbar .scrollto', true)
  const navbarlinksActive = () => {
    let position = window.scrollY + 200
    navbarlinks.forEach(navbarlink => {
      if (!navbarlink.hash) return
      let section = select(navbarlink.hash)
      if (!section) return
      if (position >= section.offsetTop && position <= (section.offsetTop + section.offsetHeight)) {
        navbarlink.classList.add('active')
      } else {
        navbarlink.classList.remove('active')
      }
    })
  }
  window.addEventListener('load', navbarlinksActive)
  onscroll(document, navbarlinksActive)

  /**
   * Scrolls to an element with header offset
   */
  const scrollto = (el) => {
    let header = select('#header')
    let offset = header.offsetHeight

    let elementPos = select(el).offsetTop
    window.scrollTo({
      top: elementPos - offset,
      behavior: 'smooth'
    })
  }

  /**
   * Back to top button
   */
  let backtotop = select('.back-to-top')
  if (backtotop) {
    const toggleBacktotop = () => {
      if (window.scrollY > 100) {
        backtotop.classList.add('active')
      } else {
        backtotop.classList.remove('active')
      }
    }
    window.addEventListener('load', toggleBacktotop)
    onscroll(document, toggleBacktotop)
  }

  /**
   * Mobile nav toggle
   */
  on('click', '.mobile-nav-toggle', function(e) {
    select('#navbar').classList.toggle('navbar-mobile')
    this.classList.toggle('bi-list')
    this.classList.toggle('bi-x')
  })

  /**
   * Mobile nav dropdowns activate
   */
  on('click', '.navbar .dropdown > a', function(e) {
    if (select('#navbar').classList.contains('navbar-mobile')) {
      e.preventDefault()
      this.nextElementSibling.classList.toggle('dropdown-active')
    }
  }, true)

  /**
   * Scrool with ofset on links with a class name .scrollto
   */
  on('click', '.scrollto', function(e) {
    if (select(this.hash)) {
      e.preventDefault()

      let navbar = select('#navbar')
      if (navbar.classList.contains('navbar-mobile')) {
        navbar.classList.remove('navbar-mobile')
        let navbarToggle = select('.mobile-nav-toggle')
        navbarToggle.classList.toggle('bi-list')
        navbarToggle.classList.toggle('bi-x')
      }
      scrollto(this.hash)
    }
  }, true)

  /**
   * Scroll with ofset on page load with hash links in the url
   */
  window.addEventListener('load', () => {
    if (window.location.hash) {
      if (select(window.location.hash)) {
        scrollto(window.location.hash)
      }
    }
  });

  /**
   * Preloader
   */
  let preloader = select('#preloader');
  if (preloader) {
    window.addEventListener('load', () => {
      preloader.remove()
    });
  }

  /**
   * Porfolio isotope and filter
   */
  window.addEventListener('load', () => {
    let portfolioContainer = select('.portfolio-container');
    if (portfolioContainer) {
      let portfolioIsotope = new Isotope(portfolioContainer, {
        itemSelector: '.portfolio-item'
      });

      let portfolioFilters = select('#portfolio-flters li', true);

      on('click', '#portfolio-flters li', function(e) {
        e.preventDefault();
        portfolioFilters.forEach(function(el) {
          el.classList.remove('filter-active');
        });
        this.classList.add('filter-active');

        portfolioIsotope.arrange({
          filter: this.getAttribute('data-filter')
        });
        portfolioIsotope.on('arrangeComplete', function() {
          AOS.refresh()
        });
      }, true);
    }

  });

  /**
   * Initiate portfolio lightbox 
   
  const portfolioLightbox = GLightbox({
    selector: '.portfolio-lightbox'
  });*/

  /**
   * Portfolio details slider
   
  new Swiper('.portfolio-details-slider', {
    speed: 400,
    loop: true,
    autoplay: {
      delay: 5000,
      disableOnInteraction: false
    },
    pagination: {
      el: '.swiper-pagination',
      type: 'bullets',
      clickable: true
    }
  });*/

  /**
   * Testimonials slider
  
  new Swiper('.testimonials-slider', {
    speed: 600,
    loop: true,
    autoplay: {
      delay: 5000,
      disableOnInteraction: false
    },
    slidesPerView: 'auto',
    pagination: {
      el: '.swiper-pagination',
      type: 'bullets',
      clickable: true
    },
    breakpoints: {
      320: {
        slidesPerView: 1,
        spaceBetween: 20
      },

      1200: {
        slidesPerView: 3,
        spaceBetween: 20
      }
    }
  });*/

  /**
   * Animation on scroll
   */
  window.addEventListener('load', () => {
    AOS.init({
      duration: 1000,
      easing: 'ease-in-out',
      once: true,
      mirror: false
    })
  });

})()