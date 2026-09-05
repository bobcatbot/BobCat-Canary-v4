import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { INVITE_URL } from "@/lib/discord";
import { getGuildList, type EligibleGuild } from "@/lib/dashboard";
import { LegacyStyles } from "@/components/site/legacy-styles";
import { SiteNavbar } from "@/components/site/navbar";
import { SiteScripts } from "@/components/site/scripts";

export const metadata: Metadata = { title: "Dashboard | BobCat Beta" };

/** Port of templates/dashboard/guilds.html — the server picker.
 *  Uses the marketing shell (style.css + Navbar), not the dash chrome. */
export default async function GuildPickerPage() {
  const session = await auth();
  if (!session) redirect("/login?callbackUrl=/dashboard");

  let guilds: EligibleGuild[] = [];
  try {
    ({ guilds } = await getGuildList());
  } catch {
    /* API unreachable — falls through to the "no servers" copy */
  }

  return (
    <>
      <LegacyStyles />
      <SiteNavbar user={session.user ?? null} inviteUrl={INVITE_URL} />

      <main className="mainn">
        <h2 className="text-center fs-3 fw-semibold">Select a server</h2>
        {guilds.length === 0 ? (
          <div
            className="d-flex flex-column justify-content-center align-items-center"
            style={{ marginTop: "25px", marginBottom: "25px" }}
          >
            <p className="mb-1 fs-7">
              Opps, looks like you don&apos;t have any servers.
            </p>
            <p className="mb-1 fs-7">
              Are you sure you are logged in to the correct account?
            </p>
          </div>
        ) : (
          <div
            className="d-flex flex-column justify-content-center align-items-center"
            style={{ marginTop: "25px", marginBottom: "25px" }}
          >
            <div className="server-card grid grid-cols gap-4 lg:gap-6">
              {guilds.map((guild) => (
                <a key={guild.id} href={`/dashboard/${guild.id}`}>
                  <div className="card">
                    <div className="d-flex justify-content-center align-items-center">
                      <img
                        src={guild.icon_url ?? "/legacy/discord-logo.png"}
                        className="icon"
                        width="70px"
                        alt="Server Icon"
                      />
                    </div>

                    <div className="d-flex justify-content-between align-items-center mt-3">
                      <div>
                        <h2>{guild.name}</h2>
                        <p className="m-0">{guild.perm}</p>
                      </div>
                      <span
                        className="button"
                        style={{ backgroundColor: guild.color }}
                      >
                        {guild.btn_name}
                      </span>
                    </div>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}
      </main>

      <SiteScripts />

      <style>{`
.gap {
  gap: 16px!important;
}

.p-3 {
  padding: 0.75rem!important;
}

.grid {
  display: grid;
}
.grid-cols {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.server-card {
  width: min(100vw, 850px);
}
.server-card a:hover {
  color: white;
}

.server-card .card {
  padding: 12px;
  background: #18191c;
  color: var(--text-color);
  border-radius: 8px;
}
.server-card .card .icon {
  border-radius: 100%;
  border: 2px solid white;
}
.server-card .card h2 {
  margin: 0;
  font-size: 18px;
  font-weight: bold;
}

.button {
  color: white;
  font-size: 12px;
  margin-left: 5px;
  padding: 0.5rem 1rem;
  border-radius: 0.25rem;
}

@media (max-width: 768px) {
  .server-card {
    padding-left: 15px;
    padding-right: 15px;
  }

  .grid-cols {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .m-2\\.5 {
    margin: 0.625rem;
  }
}

@media (max-width: 640px) {
  .server-card {
    padding-left: 15px;
    padding-right: 15px;
  }

  .grid-cols {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }

  .m-2\\.5 {
    margin: 0.625rem;
  }
}
`}</style>
    </>
  );
}
