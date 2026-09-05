const CLIENT_ID = process.env.NEXT_PUBLIC_DISCORD_CLIENT_ID ?? "";

/** Mirrors web_dashboard/config.py::INVITE_URL */
export const INVITE_URL =
  `https://discord.com/api/oauth2/authorize?client_id=${CLIENT_ID}` +
  `&permissions=1644905889015&scope=bot%20applications.commands`;
