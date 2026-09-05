import { quartJSON } from "@/lib/quart";
import { EconomyForm, type EconomyPayload } from "@/components/economy-form";

export default async function EconomyPage({
  params,
}: PageProps<"/dashboard/[guildId]/economy">) {
  const { guildId } = await params;

  let payload: EconomyPayload;
  try {
    payload = await quartJSON<EconomyPayload>(
      `/api/dashboard/${guildId}/economy`,
    );
  } catch (e) {
    return (
      <main className="mx-auto max-w-2xl p-10">
        <h1 className="text-xl font-semibold">Economy</h1>
        <p className="mt-4 text-red-600">
          Could not load this guild&rsquo;s economy config. You may not have
          access, or the plugin API is unreachable.
        </p>
        <pre className="mt-2 text-xs text-neutral-500">{String(e)}</pre>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl p-6 sm:p-10">
      <EconomyForm guildId={guildId} initial={payload} />
    </main>
  );
}
