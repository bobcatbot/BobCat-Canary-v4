import { quartJSON } from "./quart";

export type DashUser = { id: string; username: string; avatar_url: string };

export type DashGuild = {
  id: string;
  name: string;
  icon_url: string | null;
  member_count: number;
};

export type Role = {
  id: string;
  name: string;
  color: string;
  permissions: number;
  position: number;
  disabled: boolean;
};

export type TextChannel = {
  type: "text";
  id: string;
  name: string;
  position: number;
  can_send: boolean;
};

export type Emoji = {
  id: string;
  name: string;
  url: string;
  animated: boolean;
};

export type Plugin = {
  key: string;
  title: string;
  description: string;
  db_key: string;
  icon: string;
  url: string;
  badge: string;
  category: "management" | "utilities" | "fun" | string;
  premium: boolean;
  status: boolean;
  max: number;
  max_premium: number;
};

export type Notification = {
  id: string;
  type: "info" | "warning" | "error" | string;
  title: string;
  description: string;
  fix: string;
  link: string;
  user: string;
  read: boolean;
};

export type DashMeta = {
  user: DashUser;
  guild: DashGuild;
  notifications: { unread: Notification[]; unread_count: number };
  is_premium: boolean;
  roles: Role[];
  channels: TextChannel[];
  emojis: Emoji[];
  plugins: Plugin[];
};

export type EligibleGuild = {
  id: string;
  name: string;
  icon_url: string | null;
  perm: "Owner" | "Bot Master" | "Admin";
  is_bot_in_guild: boolean;
  btn_name: "Go" | "Setup";
  color: string;
};

export const getMeta = (guildId: string) =>
  quartJSON<DashMeta>(`/api/dashboard/${guildId}/meta`);

export const getGuildList = () =>
  quartJSON<{ user: DashUser; guilds: EligibleGuild[] }>(
    "/api/dashboard/guilds",
  );
