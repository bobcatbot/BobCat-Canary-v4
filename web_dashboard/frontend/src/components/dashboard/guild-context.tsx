"use client";

import { createContext, useContext } from "react";
import type { DashMeta } from "@/lib/dashboard";

const GuildContext = createContext<DashMeta | null>(null);

export function GuildProvider({
  meta,
  children,
}: {
  meta: DashMeta;
  children: React.ReactNode;
}) {
  return <GuildContext.Provider value={meta}>{children}</GuildContext.Provider>;
}

/** Shell data (guild, plugins, roles, channels, emojis, premium) for the
 *  current dashboard guild — populated once by the [guildId] layout. */
export function useGuild(): DashMeta {
  const ctx = useContext(GuildContext);
  if (!ctx) throw new Error("useGuild must be used within a GuildProvider");
  return ctx;
}
