"use client";

import { useEffect, useState } from "react";

export type Shard = {
  id: number;
  emoji: string;
  state: string;
  color: string;
  latency: string;
  uptime: string;
  servers: number;
  user_in_guilds: string[];
};

function formatUptime(isoString: string) {
  const since = new Date(isoString).getTime();
  const diff = Math.floor((Date.now() - since) / 1000);
  const d = Math.floor(diff / 86400);
  const h = Math.floor((diff % 86400) / 3600);
  const m = Math.floor((diff % 3600) / 60);
  const s = diff % 60;
  if (d > 0) return `${d}d`;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return `${s}s`;
}

/**
 * Port of templates/status.html — hero + main body. Renders the whole thing
 * (not just an island) so the ticking countdown can stay inside the hero
 * band exactly like the template. The static collapse card is passed in as
 * `children` from the server page.
 */
export function StatusShards({
  initial,
  loggedIn,
  children,
}: {
  initial: Shard[];
  loggedIn: boolean;
  children: React.ReactNode;
}) {
  const [shards, setShards] = useState<Shard[]>(initial);
  const [seconds, setSeconds] = useState(30);

  useEffect(() => {
    const tick = setInterval(() => {
      setSeconds((s) => {
        if (s <= 1) {
          fetch("/api/quart/api/shard_status")
            .then((r) => r.json())
            .then((data: Shard[]) => setShards(data))
            .catch((e) => console.error("Failed to update shard data:", e));
          return 30;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(tick);
  }, []);

  const badShards = shards.filter((s) => s.state !== "Ready").map((s) => s.id);

  return (
    <>
      <section className="page-header d-flex align-items-center">
        <div
          className="container d-flex flex-column align-items-center justify-content-center"
          data-aos="fade-up"
        >
          <h1>Bot status</h1>
          <p className="m-0" id="countdown">
            This page automatically refreshes every 30 seconds. Next update in:{" "}
            <span id="timer">{seconds}</span>
          </p>
        </div>
      </section>

      <main>
        {children}

        <div className="container mt-4">
          <div
            className={`alert ${
              badShards.length > 0 ? "alert-danger" : "alert-success"
            }`}
            role="alert"
          >
            {badShards.length > 0
              ? `${badShards.length} shard(s) are misbehaving`
              : "All systems are operational!"}
          </div>
        </div>

        <div
          id="shard-list"
          className="container my-4 mt-3 d-flex align-items-stretch gap-3"
        >
          {shards.map((shard) => (
            <div
              key={shard.id}
              className="position-relative shard-card"
              data-id={shard.id}
            >
              <div
                className="card"
                style={{ textAlign: "center", backgroundColor: "#223" }}
                data-color={shard.color}
                aria-describedby={`shard-${shard.id}`}
              >
                <div className="card-body">
                  <h5 className="card-title m-0" style={{ color: shard.color }}>
                    {shard.id}
                  </h5>
                  {shard.emoji ? (
                    <p className="card-text" style={{ color: shard.color }}>
                      {shard.emoji}
                    </p>
                  ) : (
                    <p className="card-text" />
                  )}
                </div>
              </div>

              <div id={`shard-${shard.id}`} role="tooltip">
                <div className="text">
                  <b className="title">Status:</b> {shard.state}
                </div>
                <div className="text">
                  <b className="title">Latency:</b> {shard.latency}
                </div>
                <div className="text">
                  <b className="title">Uptime:</b> {formatUptime(shard.uptime)}
                </div>
                <div className="text">
                  <b className="title">Servers:</b> {shard.servers}
                </div>
                {loggedIn && shard.user_in_guilds?.length > 0 && (
                  <div className="text flex-column">
                    <b className="title">Servers you may know:</b>{" "}
                    {shard.user_in_guilds.map((g) => (
                      <span key={g}>{g}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </main>
    </>
  );
}
