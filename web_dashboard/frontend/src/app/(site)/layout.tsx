import { auth } from "@/auth";
import { INVITE_URL } from "@/lib/discord";
import { SiteNavbar } from "@/components/site/navbar";
import { SiteScripts } from "@/components/site/scripts";

/**
 * Marketing / public pages. Mirrors templates/include/links.html +
 * templates/components/Navbar.html shell. Footer is rendered per-page
 * (templates/status.html omits it).
 */
export default async function SiteLayout({
  children,
}: LayoutProps<"/">) {
  const session = await auth();

  return (
    <>
      {/* Fonts */}
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
      {/* Vendor CSS — same versions as links.html */}
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
      {/* Site stylesheet last so it wins */}
      <link rel="stylesheet" href="/legacy/css/style.css" precedence="app" />

      <SiteNavbar user={session?.user ?? null} inviteUrl={INVITE_URL} />

      {children}

      <div id="preloader" />
      <a
        href="#"
        className="back-to-top d-flex align-items-center justify-content-center"
      >
        <i className="bi bi-arrow-up-short" />
      </a>

      <SiteScripts />
    </>
  );
}
