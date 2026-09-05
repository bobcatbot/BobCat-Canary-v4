import type { Metadata } from "next";
import { ErrorCard } from "@/components/dashboard/error-card";

export const metadata: Metadata = { title: "404 | BobCat" };

/**
 * Port of templates/error/NoAccess.html — shown when an authenticated user
 * lacks permission for a guild / a plugin isn't enabled. The dashboard
 * `[guildId]` layout redirects here on a 403 from `/api/dashboard/<gid>/meta`.
 */
export default function NoAccessPage() {
  return (
    <ErrorCard
      heading="Uh oh"
      message="It looks like you stumbled upon a page that isnt enabled quite yet."
    />
  );
}
