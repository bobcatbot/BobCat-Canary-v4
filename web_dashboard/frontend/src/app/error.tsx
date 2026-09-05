"use client";

import { ServerErrorCard } from "@/components/dashboard/server-error";

/** Port of templates/error/500.html — page-level error boundary. */
export default function Error() {
  return <ServerErrorCard />;
}
