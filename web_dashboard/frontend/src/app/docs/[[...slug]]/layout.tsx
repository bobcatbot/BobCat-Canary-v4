import { LegacyStyles } from "@/components/site/legacy-styles";

/**
 * templates/docs.html has its own full-screen .layout (sidebar + content) and
 * does NOT use the marketing navbar/footer — so it sits outside the (site)
 * group with a minimal shell: the legacy stylesheet stack + docs.css.
 */
export default function DocsLayout({
  children,
}: LayoutProps<"/docs/[[...slug]]">) {
  return (
    <>
      <LegacyStyles />
      <link rel="stylesheet" href="/legacy/css/docs.css" precedence="app" />
      {children}
    </>
  );
}
