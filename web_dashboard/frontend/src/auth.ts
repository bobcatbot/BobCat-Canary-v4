import NextAuth from "next-auth";
import Discord from "next-auth/providers/discord";

/**
 * Auth.js owns the Discord OAuth dance and the session cookie only.
 * Authorization (guild permissions, premium, plugin-enabled) still lives in
 * Quart's `plugin_guard`; we just forward the Discord access token to it.
 */
export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Discord({
      authorization:
        "https://discord.com/api/oauth2/authorize?scope=identify+guilds",
    }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
        token.expiresAt = account.expires_at;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string | undefined;
      return session;
    },
  },
});
