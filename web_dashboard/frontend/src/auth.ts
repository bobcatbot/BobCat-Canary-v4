import NextAuth from "next-auth";
import Discord from "next-auth/providers/discord";

/**
 * Auth.js owns the Discord OAuth dance and the session cookie only.
 * Authorization (guild permissions, premium, plugin-enabled) still lives in
 * Quart's `plugin_guard`; we forward the Discord access token to it as a
 * Bearer header (see src/lib/quart.ts).
 *
 * Scopes match web_dashboard/config.py's OAUTH_URL minus the ones the new
 * dashboard doesn't use (email, guilds.join): `identify guilds`.
 */
const DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token";

async function refreshAccessToken(refreshToken: string) {
  const res = await fetch(DISCORD_TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: process.env.AUTH_DISCORD_ID!,
      client_secret: process.env.AUTH_DISCORD_SECRET!,
      grant_type: "refresh_token",
      refresh_token: refreshToken,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw data;
  return {
    accessToken: data.access_token as string,
    refreshToken: (data.refresh_token as string) ?? refreshToken,
    expiresAt: Math.floor(Date.now() / 1000) + (data.expires_in as number),
  };
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  trustHost: true,
  pages: { signIn: "/login" },
  providers: [
    Discord({ authorization: { params: { scope: "identify guilds" } } }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      // Initial sign-in
      if (account) {
        token.accessToken = account.access_token;
        token.refreshToken = account.refresh_token;
        token.expiresAt = account.expires_at;
        return token;
      }

      // Still valid (60s skew)
      if (token.expiresAt && Date.now() / 1000 < token.expiresAt - 60) {
        return token;
      }

      // Expired — try to refresh
      if (!token.refreshToken) return { ...token, error: "NoRefreshToken" };
      try {
        const refreshed = await refreshAccessToken(token.refreshToken);
        return { ...token, ...refreshed, error: undefined };
      } catch {
        return { ...token, error: "RefreshFailed" };
      }
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      session.error = token.error;
      return session;
    },
  },
});
