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
  const res = await quartFetch(path);
  if (!res.ok) {
    throw new Error(`Quart ${path} -> ${res.status}`);
  }
  return res.json() as Promise<T>;
}
