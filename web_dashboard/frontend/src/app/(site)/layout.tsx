import { auth } from "@/auth";
import { INVITE_URL } from "@/lib/discord";
import { LegacyStyles } from "@/components/site/legacy-styles";
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
      <LegacyStyles />

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
