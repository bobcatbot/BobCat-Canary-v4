import { notFound, redirect } from "next/navigation";
import { quartFetch } from "@/lib/quart";
import { getGuildList, type DashMeta } from "@/lib/dashboard";
import { DashStyles } from "@/components/dashboard/dash-styles";
import { DashScripts } from "@/components/dashboard/dash-scripts";
import { DashNavbar } from "@/components/dashboard/dash-navbar";
import { Sidebar } from "@/components/dashboard/sidebar";
import { GuildProvider } from "@/components/dashboard/guild-context";

/**
 * Dashboard chrome for one guild — mirrors dash-links.html + DashNavbar.html +
 * Sidebar.html. Fetches /api/dashboard/<gid>/meta once and hands it to every
 * plugin page via GuildProvider. proxy.ts already gates auth; a 403 here means
 * "authed but not allowed for this guild" -> NoAccess.
 */
export default async function GuildLayout({
  children,
  params,
}: LayoutProps<"/dashboard/[guildId]">) {
  const { guildId } = await params;

  const res = await quartFetch(`/api/dashboard/${guildId}/meta`);
  if (res.status === 401) redirect(`/login?callbackUrl=/dashboard/${guildId}`);
  if (res.status === 403) redirect("/no-access");
  if (res.status === 404) notFound();
  if (!res.ok) throw new Error(`meta ${res.status}`);
  const meta = (await res.json()) as DashMeta;

  let otherGuilds: { id: string; name: string; icon_url: string | null }[] = [];
  try {
    const { guilds } = await getGuildList();
    otherGuilds = guilds
      .filter((g) => g.is_bot_in_guild)
      .map((g) => ({ id: g.id, name: g.name, icon_url: g.icon_url }));
  } catch {
    otherGuilds = [
      { id: meta.guild.id, name: meta.guild.name, icon_url: meta.guild.icon_url },
    ];
  }

  return (
    <>
      <DashStyles />
      <GuildProvider meta={meta}>
        <DashNavbar meta={meta} />
        <Sidebar meta={meta} otherGuilds={otherGuilds} />
        {children}
      </GuildProvider>
      <DashScripts />
    </>
  );
}
