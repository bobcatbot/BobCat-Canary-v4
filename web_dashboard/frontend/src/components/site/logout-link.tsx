"use client";

import { signOut } from "next-auth/react";

/** Matches the old <a href="/oauth/logout"> — click signs out immediately. */
export function LogoutLink({
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
      onClick={() => signOut({ redirectTo: "/" })}
    >
      {children}
    </a>
  );
}
