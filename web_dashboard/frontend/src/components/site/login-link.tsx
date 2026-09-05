"use client";

import { signIn } from "next-auth/react";

/**
 * Matches the old Navbar behaviour: one click goes straight to Discord.
 * (The `/login` page is only the interstitial proxy.ts shows when an
 * unauthenticated request hits a protected route.)
 */
export function LoginLink({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <a
      className={className}
      style={{ cursor: "pointer" }}
      onClick={() => signIn("discord", { redirectTo: "/dashboard" })}
    >
      {children}
    </a>
  );
}
