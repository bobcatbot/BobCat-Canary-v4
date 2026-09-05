import type { Session } from "next-auth";
import { InviteLink } from "./invite-link";

/** Port of templates/components/Navbar.html */
export function SiteNavbar({
  user,
  inviteUrl,
}: {
  user: Session["user"] | null;
  inviteUrl: string;
}) {
  return (
    <header id="header" className="fixed-top">
      <div className="container d-flex align-items-center justify-content-between">
        <h1 className="logo">
          <a href="/">BobCat Inc</a>
        </h1>

        <nav id="navbar" className="navbar">
          <i className="bi bi-list mobile-nav-toggle" />
          <ul className="navbar-ul">
            <li>
              <a className="nav-link scrollto active" href="/">
                Home
              </a>
            </li>
            <li>
              <a className="nav-link scrollto" href="/#about">
                About
              </a>
            </li>
            <li className="dropdown">
              <a href="/#plugins">
                <span>Plugins</span> <i className="bi bi-chevron-down" />
              </a>
              <ul>
                <li>
                  <a href="/plugins/management">Moderation &amp; Management</a>
                </li>
                <li>
                  <a href="/plugins/utilities">Utilities</a>
                </li>
                <li>
                  <a href="/plugins/engagement-and-fun">Engagement &amp; Fun</a>
                </li>
              </ul>
            </li>
            <li>
              <a className="nav-link scrollto" href="/#team">
                Team
              </a>
            </li>
            <li>
              <InviteLink href={inviteUrl} className="nav-link">
                Invite
              </InviteLink>
            </li>

            {!user && (
              <li>
                <a href="/api/auth/signin" className="nav-profile getstarted">
                  Login with Discord
                </a>
              </li>
            )}
          </ul>

          {user && (
            <div className="dropdown">
              <a className="nav-profile nav-link gap">
                <img
                  src={user.image ?? ""}
                  alt=""
                  style={{ width: 32, height: 32, borderRadius: "50%" }}
                />
              </a>
              <ul className="nav-profile user">
                <li>
                  <a href="/dashboard">
                    <span>My servers</span>
                  </a>
                </li>

                <hr style={{ color: "lightgray", margin: "5px 0px" }} />

                <li>
                  <a href="/api/auth/signout" className="text-danger">
                    <span>Logout</span>
                  </a>
                </li>
              </ul>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}
