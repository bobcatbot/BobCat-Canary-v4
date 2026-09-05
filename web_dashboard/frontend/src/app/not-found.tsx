import type { Metadata } from "next";
import { ErrorCard } from "@/components/dashboard/error-card";

export const metadata: Metadata = { title: "404 | BobCat" };

/** Port of templates/error/404.html (Quart's @app.errorhandler(404)). */
export default function NotFound() {
  return (
    <ErrorCard
      heading="404"
      message="The page you are looking for doesn't exist."
    />
  );
}
