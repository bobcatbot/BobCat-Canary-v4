/**
 * Seasonal theme picker. Runs in <head> so data-season is set before first paint.
 *
 *   ?theme=christmas   force a season (remembered until cleared)
 *   ?theme=off         no season
 *   ?theme=auto        back to the date-based default
 *
 * With nothing forced, byDate() picks Christmas or Halloween by date and
 * leaves the standard theme the rest of the year. Winter, spring, summer
 * and autumn are defined in seasons.css but only load through ?theme=.
 */
(function () {
  'use strict';

  var KEY = 'season';
  var FX_KEY = 'season-fx';
  var root = document.documentElement;

  // Particle look per season. r = [min, max] radius.
  var FX = {
    christmas: { type: 'snow',    n: 30, r: [1, 2.2],   icon: 'bi-snow' },
    winter:    { type: 'snow',    n: 40, r: [1.5, 3.6], icon: 'bi-snow' },
    halloween: { type: 'embers',  n: 36, r: [1.2, 2.8], icon: 'bi-fire' },
    spring:    { type: 'petals',  n: 36, r: [3, 5.5],   icon: 'bi-flower1' },
    summer:    { type: 'bubbles', n: 30, r: [3, 8],     icon: 'bi-droplet' },
    autumn:    { type: 'leaves',  n: 36, r: [4, 7],     icon: 'bi-tree' }
  };
  var LEAVES = ['#e0952d', '#c2571a', '#a8321b', '#d6b13a'];

  function byDate(d) {
    var md = (d.getMonth() + 1) * 100 + d.getDate();
    if (md >= 1201 || md <= 101) return 'christmas';
    if (md >= 1015 && md <= 1102) return 'halloween';
    return null;
  }

  function pick() {
    var q = new URLSearchParams(location.search).get('theme');
    try {
      if (q === 'auto') localStorage.removeItem(KEY);
      else if (q) localStorage.setItem(KEY, q);
      q = localStorage.getItem(KEY);
    } catch (_) {}
    if (q === 'off') return null;
    if (q && FX[q]) return q;
    return byDate(new Date());
  }

  var season = pick();
  if (season) root.setAttribute('data-season', season);

  /* ---------- user theme color ---------- */
  // A season wins: the picked color is stored either way but only renders
  // while no season is active.
  var ACCENT_KEY = 'accent';
  var DEFAULT_ACCENT = '#5865f2';

  function stored() {
    try {
      var v = localStorage.getItem(ACCENT_KEY);
      return /^#[0-9a-f]{6}$/i.test(v) ? v.toLowerCase() : null;
    } catch (_) { return null; }
  }

  // Keep the lightness in a range where white button text and a dark page both work.
  function hsl(hex) {
    var r = parseInt(hex.substr(1, 2), 16) / 255,
        g = parseInt(hex.substr(3, 2), 16) / 255,
        b = parseInt(hex.substr(5, 2), 16) / 255;
    var max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
    var l = (max + min) / 2, s = 0, hue = 0;
    if (d) {
      s = d / (1 - Math.abs(2 * l - 1));
      hue = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
      hue = (hue * 60 + 360) % 360;
    }
    l = Math.min(Math.max(l, 0.38), 0.66);
    return 'hsl(' + Math.round(hue) + ' ' + Math.round(s * 100) + '% ' + Math.round(l * 100) + '%)';
  }

  function applyAccent(hex) {
    if (season || !hex || hex === DEFAULT_ACCENT) {
      root.removeAttribute('data-accent');
      root.style.removeProperty('--accent-color');
      return;
    }
    root.style.setProperty('--accent-color', hsl(hex));
    root.setAttribute('data-accent', 'custom');
  }

  applyAccent(stored());

  document.addEventListener('DOMContentLoaded', function () {
    var box = document.getElementById('accentPicker');
    if (!box) return;
    var swatches = box.querySelectorAll('.accent-swatch[data-color]');
    var custom = document.getElementById('accentCustom');
    document.getElementById('accentNote').hidden = !season;

    // Keep the dropdown open while picking
    box.addEventListener('click', function (e) { e.stopPropagation(); });

    function mark(hex) {
      for (var i = 0; i < swatches.length; i++) {
        swatches[i].setAttribute('aria-pressed', String(swatches[i].dataset.color.toLowerCase() === hex));
      }
      custom.value = hex;
    }

    function choose(hex) {
      hex = hex.toLowerCase();
      try {
        if (hex === DEFAULT_ACCENT) localStorage.removeItem(ACCENT_KEY);
        else localStorage.setItem(ACCENT_KEY, hex);
      } catch (_) {}
      applyAccent(hex);
      mark(hex);
    }

    mark(stored() || DEFAULT_ACCENT);
    for (var i = 0; i < swatches.length; i++) {
      swatches[i].addEventListener('click', function () { choose(this.dataset.color); });
    }
    custom.addEventListener('input', function () { choose(custom.value); });
  });

  /* ---------- particles ---------- */
  if (!season || matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var cfg = FX[season];
  var canvas, ctx, parts = [], raf = 0, w = 0, h = 0;
  var rnd = function (a, b) { return a + Math.random() * (b - a); };
  var rises = cfg.type === 'embers' || cfg.type === 'bubbles';

  function make(initial) {
    var p = {
      x: rnd(0, w),
      y: initial ? rnd(0, h) : (rises ? h + 10 : -12),
      ph: rnd(0, 6.28), rot: rnd(0, 6.28), vr: rnd(-0.03, 0.03),
      r: rnd(cfg.r[0], cfg.r[1]), vx: rnd(-0.15, 0.15), vy: rnd(0.35, 0.9)
    };
    if (cfg.type === 'embers') p.vy = -rnd(0.4, 1);
    if (cfg.type === 'bubbles') p.vy = -rnd(0.25, 0.6);
    if (cfg.type === 'petals') p.vx = rnd(0.2, 0.6);
    if (cfg.type === 'leaves') { p.vx = rnd(-0.2, 0.4); p.col = LEAVES[Math.floor(rnd(0, 4))]; }
    return p;
  }

  function draw(p) {
    ctx.save();
    ctx.translate(p.x, p.y);
    switch (cfg.type) {
      case 'snow':
        ctx.fillStyle = 'rgba(255,255,255,.85)';
        ctx.beginPath(); ctx.arc(0, 0, p.r, 0, 6.28); ctx.fill();
        break;
      case 'embers':
        var g = ctx.createRadialGradient(0, 0, 0, 0, 0, p.r * 3);
        g.addColorStop(0, 'rgba(255,170,60,.95)');
        g.addColorStop(1, 'rgba(255,120,20,0)');
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(0, 0, p.r * 3, 0, 6.28); ctx.fill();
        break;
      case 'petals':
        ctx.rotate(p.rot);
        ctx.fillStyle = 'rgba(255,183,213,.85)';
        ctx.beginPath(); ctx.ellipse(0, 0, p.r, p.r * 0.55, 0, 0, 6.28); ctx.fill();
        break;
      case 'bubbles':
        ctx.strokeStyle = 'rgba(190,255,245,.55)';
        ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.arc(0, 0, p.r, 0, 6.28); ctx.stroke();
        break;
      case 'leaves':
        ctx.rotate(p.rot);
        ctx.fillStyle = p.col;
        ctx.beginPath();
        ctx.moveTo(-p.r, 0);
        ctx.quadraticCurveTo(0, -p.r * 0.9, p.r, 0);
        ctx.quadraticCurveTo(0, p.r * 0.9, -p.r, 0);
        ctx.fill();
        break;
    }
    ctx.restore();
  }

  function frame() {
    ctx.clearRect(0, 0, w, h);
    var sway = (cfg.type === 'snow' || cfg.type === 'leaves') ? 0.4 : 0.25;
    for (var i = 0; i < parts.length; i++) {
      var p = parts[i];
      p.ph += 0.02; p.rot += p.vr;
      p.x += p.vx + Math.sin(p.ph) * sway;
      p.y += p.vy;
      if (p.y > h + 14 || p.y < -14 || p.x > w + 14 || p.x < -14) { parts[i] = make(false); continue; }
      draw(p);
    }
    raf = requestAnimationFrame(frame);
  }

  function resize() {
    var d = Math.min(window.devicePixelRatio || 1, 2);
    w = innerWidth; h = innerHeight;
    canvas.width = w * d; canvas.height = h * d;
    ctx.setTransform(d, 0, 0, d, 0, 0);
  }

  function start() {
    canvas.hidden = false;
    parts = [];
    for (var i = 0; i < cfg.n; i++) parts.push(make(true));
    raf = requestAnimationFrame(frame);
  }

  function stop() {
    cancelAnimationFrame(raf);
    canvas.hidden = true;
  }

  function fxOn() {
    try { return localStorage.getItem(FX_KEY) !== 'off'; } catch (_) { return true; }
  }

  function addToggle(on) {
    var bar = document.querySelector('.header-actions-desktop');
    if (!bar) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'header-action season-fx-toggle';
    btn.title = 'Toggle seasonal effects';
    btn.innerHTML = '<i class="bi ' + cfg.icon + '"></i>';
    btn.style.opacity = on ? '1' : '.5';
    btn.addEventListener('click', function () {
      on = !on;
      btn.style.opacity = on ? '1' : '.5';
      try { localStorage.setItem(FX_KEY, on ? 'on' : 'off'); } catch (_) {}
      on ? start() : stop();
    });
    bar.insertBefore(btn, bar.firstChild);
  }

  document.addEventListener('DOMContentLoaded', function () {
    canvas = document.createElement('canvas');
    canvas.className = 'season-fx';
    canvas.setAttribute('aria-hidden', 'true');
    document.body.appendChild(canvas);
    ctx = canvas.getContext('2d');
    resize();
    addEventListener('resize', resize);

    var on = fxOn();
    addToggle(on);
    if (on) start(); else canvas.hidden = true;
  });
})();
