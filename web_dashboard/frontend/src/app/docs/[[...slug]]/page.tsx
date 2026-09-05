import type { Metadata } from "next";
import { DocsRuntime } from "@/components/site/docs-runtime";

export const metadata: Metadata = { title: "Docs | BobCat" };

/** Port of templates/docs.html. web.py resolved initial_page as
 *  page_id || section || 'home'; here it's the last path segment. */
export default async function DocsPage({
  params,
}: PageProps<"/docs/[[...slug]]">) {
  const { slug } = await params;
  const initialPage = slug?.[slug.length - 1] ?? "home";

  return (
    <>
      <script
        dangerouslySetInnerHTML={{
          __html: `window.__DOCS_INITIAL_PAGE__ = ${JSON.stringify(initialPage)};`,
        }}
      />

      <div className="layout">
        <aside className="sidebar">
          <div className="sidebar-header">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <span>Docs | BobCat</span>
          </div>

          <nav className="sidebar-nav" id="sidebarNav" />
        </aside>

        <main className="content" id="mainContent" />
      </div>

      <DocsRuntime />
    </>
  );
}
