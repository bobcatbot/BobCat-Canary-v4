"use client";

import { usePathname } from "next/navigation";
import type { DashMeta } from "@/lib/dashboard";
import { BadgeBeta, SidebarBadge } from "./badges";
import { PluginDisabledModal } from "./plugin-disabled-modal";
import { PluginHoverCard } from "./plugin-hovercard";

type OtherGuild = { id: string; name: string; icon_url: string | null };

const CATEGORIES: [string, string][] = [
  ["Server Management", "management"],
  ["Utilities", "utilities"],
  ["Games & Fun", "fun"],
];

/** Port of templates/components/Sidebar.html */
export function Sidebar({
  meta,
  otherGuilds,
}: {
  meta: DashMeta;
  otherGuilds: OtherGuild[];
}) {
  const pathname = usePathname() ?? "";
  const { guild, user, plugins, is_premium } = meta;

  const section = pathname.split("/")[3] ?? "";
  const gid = guild.id;

  return (
    <>
      <aside id="sidebar" className="sidebar">
        <div className="guild-selector">
          <div className="info">
            <div className="d-flex align-items-center" style={{ gap: "5px" }}>
              <img src={guild.icon_url ?? "/legacy/discord-logo.png"} alt="" />
              {guild.name}
            </div>
            <i className="bi bi-chevron-down" />
          </div>
          <div className="content">
            <a href="/profile" className="user">
              <img src={user.avatar_url} alt="" />
              My Profile
            </a>
            <hr />
            {otherGuilds.map((g) => (
              <a
                key={g.id}
                href={`/dashboard/${g.id}${section ? "/" + section : ""}`}
                className={`guild ${g.id === gid ? "active" : ""}`}
              >
                <img src={g.icon_url ?? "/legacy/discord-logo.png"} alt="" />
                {g.name}
              </a>
            ))}
            <hr />
            <a href="/dashboard">
              <i className="bi bi-plus-lg" />
              Add a new server
            </a>
          </div>
        </div>

        <ul className="sidebar-nav" id="sidebar-nav">
          <li className="navbar-item plugin" data-active="False">
            <a className="navbar-link dashboard" data-href={`/dashboard/${gid}`}>
              <div className="d-flex">
                <span className="material-icons">dashboard</span>
                <p className="m-0">Dashboard</p>
              </div>
            </a>
          </li>
          <li className="navbar-item plugin" data-active="False" hidden>
            <a className="navbar-link" data-href={`/dashboard/${gid}/insights`}>
              <div className="d-flex">
                <span className="material-icons">insights</span>
                <p className="m-0">insights</p>
              </div>
            </a>
          </li>
          <li className="navbar-item plugin" data-active="False" hidden>
            <a
              className="navbar-link custom-bot"
              data-href={`/dashboard/${gid}/custom-bot`}
              data-enable="False"
            >
              <div className="d-flex">
                <span className="material-icons">mood</span>
                <p className="m-0">Bot Personalizer</p>
              </div>
              <BadgeBeta />
            </a>
          </li>
          <li className="navbar-item plugin" data-active="False">
            <a
              className="navbar-link settings"
              data-href={`/dashboard/${gid}/settings`}
              data-enable="False"
            >
              <div className="d-flex">
                <span className="material-icons">settings</span>
                <p className="m-0">Settings</p>
              </div>
            </a>
          </li>
          <li className="navbar-item plugin" data-active="False">
            <a
              className="navbar-link settings"
              data-href={`/dashboard/${gid}/premium`}
              data-enable="False"
            >
              <div className="d-flex">
                <i className="bi bi-star-fill" />
                <p className="m-0">Premium</p>
              </div>
            </a>
          </li>

          {CATEGORIES.map(([title, category]) => (
            <li key={category}>
              <a
                className="navbar-heading"
                data-bs-target={`#nav-${category}`}
                data-bs-toggle="collapse"
              >
                <span>{title}</span>
                <i className="bi bi-chevron-down" />
              </a>
              <ul id={`nav-${category}`} className="navbar-content collapse show">
                {plugins
                  .filter((p) => p.category === category)
                  .map((plugin) => (
                    <li key={plugin.key} className="navbar-item plugin" data-active="False">
                      <a
                        className="navbar-link"
                        data-href={`/dashboard/${gid}/${plugin.url}`}
                        data-plugin={plugin.title}
                        data-key={plugin.db_key}
                        data-icon={plugin.icon}
                        data-desc={plugin.description}
                        data-enable={plugin.status ? "True" : "False"}
                        data-module-premium={plugin.premium ? "True" : "False"}
                        data-is-premium={is_premium ? "True" : "False"}
                      >
                        <div className="d-flex">
                          <div className="position-relative">
                            <span className="material-icons">{plugin.icon}</span>
                            <div className="status-indicator" />
                          </div>
                          <p className="m-0">{plugin.title}</p>
                        </div>
                        <SidebarBadge
                          badge={plugin.badge}
                          premium={plugin.premium}
                          guildPremium={is_premium}
                        />
                      </a>
                    </li>
                  ))}
              </ul>
            </li>
          ))}
        </ul>
      </aside>

      <PluginDisabledModal guildId={gid} />
      <PluginHoverCard guildId={gid} />
    </>
  );
}
