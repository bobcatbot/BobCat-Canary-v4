"use client";

import { signIn, signOut } from "next-auth/react";

type Action =
  | { action: "login" }
  | { action: "logout" }
  | { action: "invite"; href: string };

/**
 * The `<a style="cursor:pointer" onClick>` the old Navbar used for its three
 * JS-driven links. A server component can't pass an onClick across the
 * boundary, so the behaviour lives here keyed by `action`.
 */
export function ActionLink({
  className,
  children,
  ...a
}: Action & { className?: string; children: React.ReactNode }) {
  const onClick = () => {
    if (a.action === "login") signIn("discord", { redirectTo: "/dashboard" });
    else if (a.action === "logout") signOut({ redirectTo: "/" });
    else window.open(a.href, "Invite | Bobat Inc", "width=487,height=805");
  };

  return (
    <a className={className} style={{ cursor: "pointer" }} onClick={onClick}>
      {children}
    </a>
  );
}
