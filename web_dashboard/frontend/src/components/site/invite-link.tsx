"use client";

export function InviteLink({
  href,
  className,
  children,
}: {
  href: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <a
      className={className}
      style={{ cursor: "pointer" }}
      onClick={() =>
        window.open(href, "Invite | Bobat Inc", "width=487,height=805")
      }
    >
      {children}
    </a>
  );
}
