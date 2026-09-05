import type { Metadata } from "next";
import { auth } from "@/auth";
import { quartFetch } from "@/lib/quart";
import { StatusShards, type Shard } from "@/components/site/status-shards";

export const metadata: Metadata = { title: "Status | BobCat Bot" };

/** Port of templates/status.html */
export default async function StatusPage() {
  const session = await auth();

  let shards: Shard[] = [];
  try {
    const res = await quartFetch("/api/shard_status");
    if (res.ok) shards = await res.json();
  } catch {
    /* bot / API unreachable — render empty, the client poll retries */
  }

  return (
    <>
      <StatusShards initial={shards} loggedIn={Boolean(session?.user)}>
        <div className="container mt-4">
          <button
            className="collapse-button"
            type="button"
            data-bs-toggle="collapse"
            data-bs-target="#collapseExample"
            aria-expanded="false"
            aria-controls="collapseExample"
          >
            What do the letters mean? (click to expand)
          </button>
          <div className="collapse" id="collapseExample">
            <div className="collapse-card collapse-card-body">
              <p>
                <b style={{ color: "green" }}>No letter</b> - Working as
                intentional!
              </p>
              <p>
                <b style={{ color: "green" }}>C</b> - Connected. The bot has
                connected to discord, but it might not respond to all commands.
              </p>
              <p>
                <b style={{ color: "orange" }}>P</b> - Partially connected. Like
                connected, except some servers won&apos;t have any commands work.
              </p>
              <p>
                <b style={{ color: "orange" }}>L</b> - Currently in the process of
                logging in.
              </p>
              <p>
                <b style={{ color: "red" }}>Q</b> - Offline and waiting for its
                turn to log in.
              </p>
              <p>
                <b style={{ color: "red" }}>🔥</b> - Not only is the cluster
                offline, it hasn&apos;t shown any signs it&apos;s trying to
                reconnect.
              </p>
            </div>
          </div>
        </div>
      </StatusShards>

      <style>{`
  .page-header {
    padding: 120px 0px 70px 0px;
    position: relative;
    width: 100%;
    height: 100%;
    color: #ffffff;
    background: #36393F;
    border-bottom: 2px solid #36393F;
    text-align: center;
  }

  [role="tooltip"],
  .hidetooltip + [role="tooltip"] {
    visibility: hidden;
    position: absolute;
    top: 108%;
    left: 40%;
    z-index: 1;
    width: max-content;
    padding: 6px;
    background: black;
    color: white;
    border-radius: 8px;
    transform: translate(-50%, 0);
  }
  [aria-describedby]:hover,
  [aria-describedby]:focus {
    position: relative;
  }
  [aria-describedby]:hover + [role="tooltip"],
  [aria-describedby]:focus + [role="tooltip"] {
    visibility: visible;
  }

  [role="tooltip"]::before,
  .hidetooltip + [role="tooltip"]::before {
    content: "";
    position: absolute;
    top: -14px;
    left: 50%;
    z-index: 1;
    width: 0;
    height: 0;
    transform: translate(0, -50%);
    border-width: 5px;
    border-style: solid;
    border-color: black transparent transparent transparent;
    rotate: 180deg;
  }
  @media (max-width: 480px) {
    [role="tooltip"] {
      left: 130%;
      right: 130%;
    }
    [role="tooltip"]::before {
      left: 22px;
      right: 22px;
    }
  }

  .text {
    display: flex;
    column-gap: 4px;
    color: #e4e7ea;
    font-size: 13px;
  }

  .title {
    font-weight: normal;
    color: #ffffff;
  }

  .collapse-button {
    padding: 0;
    background-color: transparent;
    color: white;
    border: none;
    cursor: pointer;
    transition-duration: 0.4s;
  }

  .collapse-card {
    background: transparent;
    margin-top: 4px;
    border: none;
  }
  .collapse-card.collapse-card-body p {
    margin: 0;
  }
`}</style>
    </>
  );
}
