/**
 * =======================================================
 * Template Name: TrendyAdmin - Bootstrap Admin Template
 * Template URL: https://bootstrapmade.com/trendy-admin-bootstrap-dashboard-template/
 * Updated: Jul 29, 2026
 * Author: BootstrapMade.com
 * License: https://bootstrapmade.com/license/
 * =======================================================
 */
/**
 * Theme JavaScript - Dark mode is enforced for this template.
 */
(function() {
  'use strict';

  const THEME_KEY = 'theme';
  const DARK_THEME = 'dark';

  function setDarkTheme() {
    document.documentElement.setAttribute('data-theme', DARK_THEME);
    try {
      localStorage.setItem(THEME_KEY, DARK_THEME);
    } catch (_) {
      // ignore storage errors (e.g., privacy mode)
    }
  }

  function initTheme() {
    setDarkTheme();
  }

  initTheme();

  window.Theme = {
    toggle: function() {
      setDarkTheme();
    },
    setDark: function() {
      setDarkTheme();
    },
    setLight: function() {
      setDarkTheme();
    },
    isDark: function() {
      return true;
    },
    getTheme: function() {
      return DARK_THEME;
    }
  };
})();