"use client";

import { useGuild } from "@/components/dashboard/guild-context";
import { PremiumModal } from "@/components/dashboard/premium-modal";
import { PluginCard } from "@/components/dashboard/plugin-card";

/** Port of templates/dashboard/dashboard.html */
export default function DashboardHome() {
  const { guild, plugins, is_premium } = useGuild();

  const inCat = (c: string) => plugins.filter((p) => p.category === c);

  return (
    <main id="main" className="main">
      <div className="pagetitle">
        <h1>Plugins</h1>
      </div>

      <div className="overview">
        <h4 className="title">DETAILS</h4>
        <div className="info">
          <div className="d-flex gap-2">
            <img
              src={guild.icon_url ?? "/legacy/discord-logo.png"}
              alt=""
              style={{ width: "52px", height: "52px", borderRadius: "50%" }}
            />

            <div>
              <h2>{guild.name}</h2>
              <p>{guild.id}</p>
            </div>

            <div className="d-flex gap-1">
              {is_premium && (
                <div className="tooltipp">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="26"
                    height="26"
                    fill="rgb(var(--premium-gold))"
                    className="bi bi-star-fill"
                    viewBox="0 0 16 16"
                  >
                    <path d="M3.612 15.443c-.386.198-.824-.149-.746-.592l.83-4.73L.173 6.765c-.329-.314-.158-.888.283-.95l4.898-.696L7.538.792c.197-.39.73-.39.927 0l2.184 4.327 4.898.696c.441.062.612.636.282.95l-3.522 3.356.83 4.73c.078.443-.36.79-.746.592L8 13.187l-4.389 2.256z" />
                  </svg>
                  <span className="tooltiptext">Premium</span>
                </div>
              )}
            </div>
          </div>

          <div className="overview-col">
            <i className="bi bi-people-fill" />
            <span style={{ fontSize: "1.125rem", fontWeight: 700 }}>
              {guild.member_count}
            </span>
            Members
          </div>
        </div>
      </div>

      <section className="section">
        <ul className="nav nav-tabs nav-tabs-bordered">
          <li className="nav-item">
            <button className="nav-link active" data-bs-toggle="tab" data-bs-target="#overview">
              All Plugins
            </button>
          </li>
          <li className="nav-item">
            <button className="nav-link" data-bs-toggle="tab" data-bs-target="#server-management">
              Server Management
            </button>
          </li>
          <li className="nav-item">
            <button className="nav-link" data-bs-toggle="tab" data-bs-target="#utilities">
              Utilities
            </button>
          </li>
          <li className="nav-item">
            <button className="nav-link" data-bs-toggle="tab" data-bs-target="#games-fun">
              Games &amp; Fun
            </button>
          </li>
        </ul>
        <div className="tab-content pt-2">
          <div id="overview" className="tab-pane fade active show" role="tabpanel">
            <div className="grid">
              {plugins.map((p) => (
                <PluginCard key={p.key} plugin={p} guild={guild} isPremium={is_premium} />
              ))}
            </div>
          </div>

          <div id="server-management" className="tab-pane fade pt-3" role="tabpanel">
            <div className="grid">
              {inCat("management").map((p) => (
                <PluginCard key={p.key} plugin={p} guild={guild} isPremium={is_premium} />
              ))}
            </div>
          </div>

          <div id="utilities" className="tab-pane fade pt-3" role="tabpanel">
            <div className="grid">
              {inCat("utilities").map((p) => (
                <PluginCard key={p.key} plugin={p} guild={guild} isPremium={is_premium} />
              ))}
            </div>
          </div>

          <div id="games-fun" className="tab-pane fade pt-3" role="tabpanel">
            <div className="grid">
              {inCat("fun").map((p) => (
                <PluginCard key={p.key} plugin={p} guild={guild} isPremium={is_premium} />
              ))}
            </div>
          </div>
        </div>
      </section>

      <PremiumModal guildId={guild.id} />

      <style>{`
.grid {
  display: grid;
  grid-template-columns: repeat(4,minmax(0,1fr));
  gap: 12px;
}

.card {
  background-color: var(--color-card-1);
  padding: 15px;
  border: none;
  border-radius: 5px;
  box-shadow: 0px 0 30px rgba(1, 41, 112, 0.1);
  height: 100%;
}
.card:hover {
  background-color: var(--color-card-2);
}

.card-logo {
  width: 60px;
  height: 56px;
  color: #fff;
  background-color: var(--color-secondary-2);
  border-radius: 8px;
  display: flex;
  justify-content: center;
  align-items: center;
}
.card-logo span,
.card-logo i {
  display: flex;
  font-size: 40px;
}
.card:hover .card-logo {
  background-color: var(--color-secondary-1);
}

.card-header {
  border-color: #ebeef4;
  background-color: #fff;
  color: #798eb3;
  padding: 15px;
}

.card-body {
  padding: 0;
}

.card-title {
  padding: 15px 0 0 0;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
}

.card-text {
  color: #899bbd;
  font-size: 14px;
  font-weight: 400;
}

.card-footer {
  border-color: #ebeef4;
  background-color: #fff;
  color: #798eb3;
  padding: 15px;
}

@media (max-width: 1440px) {
  .grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 1024px) {
  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 1023px) {
  .grid {
    grid-template-columns: repeat(1, minmax(0, 1fr));
    gap: 10px;
  }
}
`}</style>
    </main>
  );
}
