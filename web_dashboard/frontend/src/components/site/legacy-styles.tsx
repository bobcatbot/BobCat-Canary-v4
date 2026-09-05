/**
 * The stylesheet stack from templates/include/links.html — the CDN bundles the
 * legacy pages assume plus /legacy/css/style.css. Rendered by the layouts that
 * host ported Jinja pages so `<link>`s hoist into <head> with the right order
 * (framework first, site stylesheet last).
 */
export function LegacyStyles() {
  return (
    <>
      <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Balsamiq+Sans&display=swap"
        precedence="framework"
      />
      <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/icon?family=Material+Icons"
        precedence="framework"
      />
      <link
        rel="stylesheet"
        href="https://unpkg.com/aos@2.3.1/dist/aos.css"
        precedence="framework"
      />
      <link
        rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"
        precedence="framework"
      />
      <link
        rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"
        precedence="framework"
      />
      <link
        rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/glightbox/dist/css/glightbox.min.css"
        precedence="framework"
      />
      <link
        rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css"
        precedence="framework"
      />
      <link rel="stylesheet" href="/legacy/css/style.css" precedence="app" />
    </>
  );
}
