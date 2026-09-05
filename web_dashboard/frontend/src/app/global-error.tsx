"use client";

import { ServerErrorCard } from "@/components/dashboard/server-error";

/**
 * Port of templates/error/500.html — root boundary (replaces the root layout
 * too, so it renders its own <html>/<body> like the standalone template did).
 */
export default function GlobalError() {
  return (
    <html lang="en">
      <body>
        <ServerErrorCard />
      </body>
    </html>
  );
}
