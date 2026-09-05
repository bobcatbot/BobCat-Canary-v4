"use client";

import { useEffect } from "react";

/**
 * Vendor + dash JS from templates/include/dash-links.html, loaded in the same
 * order. The legacy dash/js/*.js run verbatim (index.js and main.js are lightly
 * patched — vendor `typeof` guards, and a `__ready` shim in main.js — so they
 * survive being injected after `window load`).
 *
 * Everything is appended with `async = false` so execution order is preserved
 * (dash/index.js calls `tinymce.init()` etc., so the vendors must run first).
 */
const SCRIPTS = [
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js",
  "https://unpkg.com/aos@2.3.1/dist/aos.js",
  "https://unpkg.com/boxicons@2.1.4/dist/boxicons.js",
  "https://cdn.jsdelivr.net/gh/mcstudios/glightbox/dist/js/glightbox.min.js",
  "https://unpkg.com/isotope-layout@3/dist/isotope.pkgd.min.js",
  "https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js",
  "https://unpkg.com/typed.js@2.1.0/dist/typed.umd.js",
  "https://cdn.jsdelivr.net/npm/apexcharts",
  "https://cdn.quilljs.com/1.3.6/quill.js",
  "https://cdnjs.cloudflare.com/ajax/libs/tinymce/7.4.1/tinymce.min.js",
  "https://cdnjs.cloudflare.com/ajax/libs/waypoints/4.0.1/noframework.waypoints.min.js",
  "/legacy/dash/js/index.js",
  "/legacy/dash/js/main.js",
  "/legacy/dash/js/toasts.js",
  "/legacy/dash/js/dropdown.js",
];

let injected = false;

export function DashScripts() {
  useEffect(() => {
    if (injected) return;
    injected = true;

    for (const src of SCRIPTS) {
      if (document.querySelector(`script[src="${src}"]`)) continue;
      const s = document.createElement("script");
      s.src = src;
      s.async = false; // preserve execution order across the whole list
      document.body.appendChild(s);
    }

    const onAos = () => {
      (
        window as unknown as {
          AOS?: { init: (o: Record<string, unknown>) => void };
        }
      ).AOS?.init({
        duration: 1000,
        easing: "ease-in-out",
        once: true,
        mirror: false,
      });
    };
    // AOS is early in the list; init once the whole batch has settled.
    window.addEventListener("load", onAos);
    const t = setTimeout(onAos, 1500);
    return () => {
      window.removeEventListener("load", onAos);
      clearTimeout(t);
    };
  }, []);

  return null;
}
