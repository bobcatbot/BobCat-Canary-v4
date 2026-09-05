import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { auth, signIn } from "@/auth";

export const metadata: Metadata = { title: "Login | BobCat Bot" };

/**
 * Port of templates/login.html — the "you need to sign in" interstitial.
 * Auth.js is pointed here via `pages.signIn` (src/auth.ts), so it also
 * receives the `callbackUrl` when proxy.ts bounces an unauthed dashboard hit.
 */
export default async function LoginPage({
  searchParams,
}: PageProps<"/login">) {
  const { callbackUrl } = await searchParams;
  const target = typeof callbackUrl === "string" ? callbackUrl : "/dashboard";

  if (await auth()) redirect(target);

  return (
    <div
      style={{
        minHeight: "100dvh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
      }}
    >
      <main className="mainn" style={{ textAlign: "center" }}>
        <img src="/legacy/img/bobcat.png" alt="" />

        <div>
          <h2>Welcome to BobCat&apos;s dashboard</h2>
          <p>You need to login with your Discord account to access this feature.</p>
        </div>

        <form
          action={async () => {
            "use server";
            await signIn("discord", { redirectTo: target });
          }}
        >
          <button type="submit" className="btn btn-blurple">
            Login with Discord
          </button>
        </form>
      </main>
    </div>
  );
}
