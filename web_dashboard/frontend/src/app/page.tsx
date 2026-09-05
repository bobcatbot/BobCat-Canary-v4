import { auth, signIn, signOut } from "@/auth";

export default async function Home() {
  const session = await auth();

  return (
    <main className="mx-auto max-w-xl p-10 space-y-6">
      <h1 className="text-2xl font-semibold">BobCat Dashboard (Next.js)</h1>

      {session?.user ? (
        <div className="space-y-4">
          <p>
            Signed in as <strong>{session.user.name}</strong>
          </p>
          <p className="text-sm text-neutral-500">
            Open a guild page:{" "}
            <code>/dashboard/&lt;guildId&gt;/economy</code>
          </p>
          <form
            action={async () => {
              "use server";
              await signOut();
            }}
          >
            <button className="rounded bg-neutral-200 px-4 py-2 text-sm">
              Sign out
            </button>
          </form>
        </div>
      ) : (
        <form
          action={async () => {
            "use server";
            await signIn("discord");
          }}
        >
          <button className="rounded bg-indigo-600 px-4 py-2 text-white">
            Sign in with Discord
          </button>
        </form>
      )}
    </main>
  );
}
