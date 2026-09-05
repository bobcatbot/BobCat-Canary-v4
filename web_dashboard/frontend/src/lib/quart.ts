import { auth } from "@/auth";

const BASE = process.env.QUART_API_URL ?? "http://localhost:8000";

/**
 * Server-side fetch to the Quart API with the caller's Discord token attached.
 * Use from Server Components and Route Handlers only.
 */
export async function quartFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const session = await auth();
  const headers = new Headers(init.headers);
  if (session?.accessToken) {
    headers.set("Authorization", `Bearer ${session.accessToken}`);
  }
  return fetch(`${BASE}${path}`, { ...init, headers, cache: "no-store" });
}

export async function quartJSON<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await quartFetch(path);
  } catch (e) {
    console.error(
      `[quart] ${path} — request failed (is the bot/Quart API up at ${BASE}?)`,
      e,
    );
    throw e;
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    console.error(`[quart] ${path} -> ${res.status} ${res.statusText} ${body.slice(0, 300)}`);
    throw new Error(`Quart ${path} -> ${res.status}`);
  }
  return res.json() as Promise<T>;
}
