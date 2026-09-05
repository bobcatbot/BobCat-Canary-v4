"use client";

import Script from "next/script";

/**
 * Runs the (verbatim) docs SPA script from templates/docs.html. The script
 * builds #sidebarNav / #mainContent from its own `pages` array and renders
 * markdown with `marked`, so `marked` must load first; docs.js is appended
 * from its onLoad. The initial page id is handed over on `window` (the
 * template had it as a Jinja interpolation) — set synchronously by an inline
 * script in the page so it's present before docs.js runs.
 */
export function DocsRuntime() {
  return (
    <Script
      src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"
      strategy="afterInteractive"
      onLoad={() => {
        const s = document.createElement("script");
        s.src = "/legacy/js/docs.js";
        document.body.appendChild(s);
      }}
    />
  );
}
