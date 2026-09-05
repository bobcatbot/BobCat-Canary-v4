"use client";

import Script from "next/script";

/**
 * Vendor + dash JS from templates/include/dash-links.html. The legacy
 * dash/js/*.js files are loaded verbatim (main.js is lightly patched so its
 * `window load` / `DOMContentLoaded` bodies still run when injected after
 * those events — see the `__ready` shim). They must load after the Bootstrap
 * bundle (main.js uses `bootstrap.Modal`), so they're appended from its
 * onLoad in order.
 */
const DASH_JS = [
  "/legacy/dash/js/index.js",
  "/legacy/dash/js/main.js",
  "/legacy/dash/js/toasts.js",
  "/legacy/dash/js/dropdown.js",
];

export function DashScripts() {
  return (
    <>
      <Script
        src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"
        strategy="afterInteractive"
        onLoad={() => {
          for (const src of DASH_JS) {
            if (document.querySelector(`script[src="${src}"]`)) continue;
            const s = document.createElement("script");
            s.src = src;
            s.async = false; // preserve execution order
            document.body.appendChild(s);
          }
        }}
      />
      <Script
        src="https://unpkg.com/aos@2.3.1/dist/aos.js"
        strategy="afterInteractive"
        onLoad={() =>
          (
            window as unknown as {
              AOS?: { init: (o: Record<string, unknown>) => void };
            }
          ).AOS?.init({
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
