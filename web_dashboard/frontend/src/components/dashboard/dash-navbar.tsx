import { Fragment } from "react";
import type { DashMeta } from "@/lib/dashboard";
import { ActionLink } from "@/components/site/action-link";

/** Port of templates/components/DashNavbar.html */
export function DashNavbar({ meta }: { meta: DashMeta }) {
  const { user, guild, is_premium, notifications } = meta;

  return (
    <header id="header" className="header fixed-top d-flex align-items-center">
      <div className="d-flex align-items-center justify-content-between">
        <i className="bi bi-list toggle-sidebar-btn" />

        <a href="/" className="logo d-flex justify-content-center align-items-center">
          <img src="/legacy/img/bobcat.png" alt="" />
          <span className="d-none d-md-block">BobCat</span>
        </a>
      </div>

      <nav className="header-nav ms-auto">
        <ul className="d-flex align-items-center">
          {!is_premium && (
            <li
              className="premium-upgrade nav-item me-2 btn"
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              {...({ variant: "premium" } as any)}
            >
              <a
                href="premium"
                className="d-flex"
                style={{
                  fontSize: "14px",
                  alignItems: "center",
                  gap: "4px",
                  color: "rgb(var(--premium-gold))",
                }}
              >
                <i
                  className="bi bi-star-fill"
                  style={{ fontSize: "16px", color: "rgb(var(--premium-gold))" }}
                />
                Upgrade to Premium
              </a>
            </li>
          )}

          <li className="nav-item dropdown">
            <a className="nav-link nav-icon" href="#" data-bs-toggle="dropdown">
              <i className="bi bi-bell" style={{ display: "flex", fontSize: "22px" }} />
              <span className="badge bg-primary badge-number">
                {notifications.unread_count}
              </span>
            </a>

            <ul className="dropdown-menu dropdown-menu-end dropdown-menu-arrow notifications">
              <li className="dropdown-header">
                You have {notifications.unread_count} new notifications
                <a href={`/dashboard/${guild.id}/notifications`}>
                  <span className="badge rounded-pill bg-primary p-2 ms-2">
                    View all
                  </span>
                </a>
              </li>
              <li>
                <hr className="dropdown-divider" />
              </li>
              {notifications.unread.map((n) => (
                <Fragment key={n.id}>
                  <li className="notification-item">
                    {n.type === "info" && <i className="bi bi-info-circle text-primary" />}
                    {n.type === "warning" && (
                      <i className="bi bi-exclamation-triangle text-warning" />
                    )}
                    {n.type === "error" && (
                      <i className="bi bi-exclamation-circle text-danger" />
                    )}
                    <div>
                      {n.title && <p className="notification__info__title">{n.title}</p>}
                      {n.description && (
                        <p className="notification__info__desc">{n.description}</p>
                      )}
                    </div>
                  </li>
                  <li>
                    <hr className="dropdown-divider" />
                  </li>
                </Fragment>
              ))}
            </ul>
          </li>

          <li className="nav-item dropdown pe-4">
            <a
              className="nav-link nav-profile d-flex align-items-center pe-0"
              href="#"
              data-bs-toggle="dropdown"
            >
              <img src={user.avatar_url} alt="Profile" className="rounded-circle" />
              <span className="d-none d-md-block dropdown-toggle ps-2">
                {user.username}
              </span>
            </a>

            <ul className="dropdown-menu dropdown-menu-end dropdown-menu-arrow profile">
              <li style={{ fontSize: "14px", fontWeight: 700 }}>Server Owners</li>
              <li>
                <a className="dropdown-item d-flex align-items-center" href="/dashboard">
                  My Servers
                </a>
              </li>

              <li>
                <hr className="dropdown-divider" />
              </li>
              <li>
                <ActionLink
                  action="logout"
                  className="dropdown-item d-flex align-items-center"
                >
                  Sign Out
                </ActionLink>
              </li>
            </ul>
          </li>
        </ul>
      </nav>
    </header>
  );
}
