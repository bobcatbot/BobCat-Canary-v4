import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "BobCat Bot",
  description: "BobCat Discord bot dashboard",
  icons: { icon: "/legacy/img/bobcat.png", apple: "/legacy/img/apple-touch-icon.png" },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
