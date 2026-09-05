"use client";

import Script from "next/script";
import { useEffect } from "react";

declare global {
  interface Window {
    AOS?: { init: (o: Record<string, unknown>) => void; refresh: () => void };
    bootstrap?: { Toast: new (el: Element) => { show: () => void; hide: () => void } };
  }
}

/**
 * Vendor bundles + the behaviour from static/js/index.js and static/js/main.js.
 * Reimplemented (not the legacy IIFEs) because those hang handlers off
 * `window load`, which has already fired by the time client scripts run here.
 */
export function SiteScripts() {
  useEffect(() => {
    const header = document.querySelector<HTMLElement>("#header");
    const backtotop = document.querySelector(".back-to-top");
    const navbarlinks = [
      ...document.querySelectorAll<HTMLAnchorElement>("#navbar .scrollto"),
    ];

    const onScroll = () => {
      const position = window.scrollY + 200;
      navbarlinks.forEach((link) => {
        if (!link.hash) return;
        const section = document.querySelector<HTMLElement>(link.hash);
        if (!section) return;
        const within =
          position >= section.offsetTop &&
          position <= section.offsetTop + section.offsetHeight;
        link.classList.toggle("active", within);
      });
      if (backtotop) backtotop.classList.toggle("active", window.scrollY > 100);
    };

    const scrollto = (hash: string) => {
      const el = document.querySelector<HTMLElement>(hash);
      if (!el) return;
      window.scrollTo({
        top: el.offsetTop - (header?.offsetHeight ?? 0),
        behavior: "smooth",
      });
    };

    const onNavClick = (e: Event) => {
      const a = (e.target as HTMLElement).closest<HTMLAnchorElement>(".scrollto");
      if (!a || !a.hash || !document.querySelector(a.hash)) return;
      e.preventDefault();
      const navbar = document.querySelector("#navbar");
      if (navbar?.classList.contains("navbar-mobile")) {
        navbar.classList.remove("navbar-mobile");
        document
          .querySelector(".mobile-nav-toggle")
          ?.classList.toggle("bi-list");
        document.querySelector(".mobile-nav-toggle")?.classList.toggle("bi-x");
      }
      scrollto(a.hash);
    };

    const onToggle = function (this: HTMLElement) {
      document.querySelector("#navbar")?.classList.toggle("navbar-mobile");
      this.classList.toggle("bi-list");
      this.classList.toggle("bi-x");
    };
    const toggleBtn = document.querySelector<HTMLElement>(".mobile-nav-toggle");

    document.addEventListener("scroll", onScroll);
    document.addEventListener("click", onNavClick);
    toggleBtn?.addEventListener("click", onToggle);
    onScroll();
    if (window.location.hash) scrollto(window.location.hash);
    document.querySelector("#preloader")?.remove();

    // static/js/main.js — flash toast
    const toastBS = document.getElementById("ToastBS");
    if (toastBS && window.bootstrap) {
      const t = new window.bootstrap.Toast(toastBS);
      t.show();
      setTimeout(() => t.hide(), 8000);
    }

    return () => {
      document.removeEventListener("scroll", onScroll);
      document.removeEventListener("click", onNavClick);
      toggleBtn?.removeEventListener("click", onToggle);
    };
  }, []);

  return (
    <>
      <Script
        src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"
        strategy="afterInteractive"
      />
      <Script src="https://unpkg.com/boxicons@2.1.4/dist/boxicons.js" strategy="afterInteractive" />
      <Script
        src="https://unpkg.com/aos@2.3.1/dist/aos.js"
        strategy="afterInteractive"
        onLoad={() =>
          window.AOS?.init({
            duration: 1000,
            easing: "ease-in-out",
            once: true,
            mirror: false,
          })
        }
      />
    </>
  );
}
