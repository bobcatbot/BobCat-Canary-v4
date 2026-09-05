"use client";

import type { DashGuild, Plugin } from "@/lib/dashboard";
import { BadgeNew, BadgeBeta, BadgeSoon, BadgePrem } from "./badges";

declare global {
  interface Window {
    handlePremiumOnClick?: (e: unknown) => void;
  }
}

/** Port of the `plugin_card` macro in templates/dashboard/dashboard.html. */
export function PluginCard({
  plugin,
  guild,
  isPremium,
}: {
  plugin: Plugin;
  guild: DashGuild;
  isPremium: boolean;
}) {
  return (
    <a
      className="plugin"
      data-href={`${guild.id}/${plugin.url}`}
      data-premium={String(plugin.premium)}
      data-server-premium={String(isPremium)}
      data-key={plugin.db_key}
      data-enabled={String(plugin.status)}
      data-plugin-name={plugin.title}
      onClick={(e) => window.handlePremiumOnClick?.(e)}
    >
      <div className="card">
        <div className="d-flex justify-content-between">
          <div className="card-logo">
            <span className="material-icons">{plugin.icon}</span>
          </div>
          <div className="d-flex gap-1">
            {plugin.badge === "new" && <BadgeNew />}
            {plugin.badge === "beta" && <BadgeBeta />}
            {plugin.badge === "soon" && <BadgeSoon />}
            {plugin.badge === "prem" && <BadgePrem />}
            {plugin.badge === "prem-beta" && (
              <>
                <BadgePrem />
                <BadgeBeta />
              </>
            )}
          </div>
        </div>
        <div className="card-body d-flex flex-column">
          <h5 className="card-title">{plugin.title}</h5>
          <p className="card-text">{plugin.description}</p>
          <div style={{ marginTop: "auto", width: "max-content" }}>
            {plugin.status ? (
              <span className="btn btn-blurple">
                <i className="bi bi-check2-square" /> Active
              </span>
            ) : (
              <span className="btn btn-secondary">
                <i className="bi bi-plus" /> Enable
              </span>
            )}
          </div>
        </div>
      </div>
    </a>
  );
}
