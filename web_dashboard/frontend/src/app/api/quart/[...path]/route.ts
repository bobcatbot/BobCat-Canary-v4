import { quartFetch } from "@/lib/quart";

/**
 * Authenticated pass-through to the Quart API for client-side calls
 * (TanStack Query mutations). The browser never sees the Discord token;
 * this handler injects it. `/api/quart/dashboard/123/data/post` -> Quart
 * `/dashboard/123/data/post`.
 */
async function proxy(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const search = new URL(req.url).search;
  const body =
    req.method === "GET" || req.method === "HEAD" ? undefined : await req.text();

  const res = await quartFetch(`/${path.join("/")}${search}`, {
    method: req.method,
    headers: { "Content-Type": req.headers.get("Content-Type") ?? "application/json" },
    body,
  });

  return new Response(res.body, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("Content-Type") ?? "application/json" },
  });
}

export {
  proxy as GET,
  proxy as POST,
  proxy as PUT,
  proxy as PATCH,
  proxy as DELETE,
};
