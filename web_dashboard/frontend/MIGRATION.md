# Dashboard → Next.js migration

Moving the dashboard UI off Jinja/HTML onto Next.js (App Router). Quart stays —
it becomes the JSON API, because it shares a process with the Discord bot and is
the only thing with live `v.client` access (guilds, channels, roles, premium).

```
discord.py bot ─┬─ Quart (index.py:8000)  → JSON API + existing action routes
                └─ shared event loop / Beanie models

Next.js (frontend/:3000) → all UI. Server Components fetch Quart directly;
                            client mutations go via /api/quart/* (token injected)
```

## Auth

Auth.js (`next-auth` v5) owns **only** the Discord OAuth flow + session cookie.
Authorization stays in Quart's `plugin_guard` (permission / premium /
plugin-enabled). The Discord `access_token` is stored in the Auth.js JWT and
forwarded to Quart as `Authorization: Bearer <token>`.

- `src/auth.ts` — provider + callbacks
- `src/proxy.ts` — redirects unauthenticated `/dashboard/*` to sign-in
- `web_dashboard/utils.py::current_token()` — reads the Bearer header **or** the
  legacy `session["token"]` cookie, so the same blueprints serve both frontends
  during the migration. Used by `bearer_client()`, `plugin_guard`, and
  `dashboard.py::data_post`.

## What's wired up (POC)

| Piece | File |
|---|---|
| Quart JSON API | `web_dashboard/blueprints/api.py` (`/api/dashboard/<gid>/meta`, `/api/dashboard/<gid>/economy`) |
| Server fetch helper | `frontend/src/lib/quart.ts` |
| Authed client proxy | `frontend/src/app/api/quart/[...path]/route.ts` |
| Economy page (RSC) | `frontend/src/app/dashboard/[guildId]/economy/page.tsx` |
| Economy form (client) | `frontend/src/components/economy-form.tsx` |

Writes still hit the **existing unchanged** endpoint
`POST /dashboard/<gid>/data/post` (via the `/api/quart` proxy). No write-path
logic was duplicated.

## Running both

```bash
# terminal 1 — bot + Quart API (existing)
python main.py

# terminal 2 — Next.js
cd web_dashboard/frontend
cp .env.example .env.local   # fill AUTH_SECRET + AUTH_DISCORD_ID/SECRET
npm run dev
```

Add `http://localhost:3000/api/auth/callback/discord` to the Discord app's
OAuth redirects. Then visit `http://localhost:3000`, sign in, open
`/dashboard/<guildId>/economy`.

## Phase 1 — static / marketing pages (in progress)

Decisions: keep old Jinja templates until a single final cutover; no reverse
proxy, Next runs dev-only until 100% done.

**Parity approach:** no redesign. Legacy stylesheets are copied verbatim to
`frontend/public/legacy/` (`css/style.css`, `css/dash-*.css`, `img/**`, `js/**`)
and loaded via `<link>` in the route-group layout alongside the same CDN bundles
(Bootstrap 5.3.2, Bootstrap Icons, Material Icons, Balsamiq Sans, AOS). Each
`.html` template is translated to `.tsx` keeping every class name and DOM node.
Tailwind was removed from the project — its Preflight reset fought Bootstrap.

| Page | Route | Status |
|---|---|---|
| `index.html` | `/` | ✅ ported |
| `terms.html` | `/terms` | ✅ ported |
| `thanks.html` | `/thanks` | ✅ ported |
| `contact-us.html` | `/contact-us` | ✅ ported |
| `web-plugins/management.html` | `/plugins/management` | ✅ ported |
| `web-plugins/utilities.html` | `/plugins/utilities` | ✅ ported |
| `web-plugins/engagement-and-fun.html` | `/plugins/engagement-and-fun` | ✅ ported |
| `login.html` | `/login` | ✅ ported (Auth.js `pages.signIn`) |
| `status.html` + `/api/shard_status` | `/status` | ⬜ needs Quart shard JSON |
| `docs.html` (1310 lines, JS-driven sections) | `/docs/[[...slug]]` | ⬜ |

Shared shell: `src/app/(site)/layout.tsx`, `src/components/site/{navbar,footer,scripts,invite-link}.tsx`.
`SiteScripts` reimplements `static/js/index.js` + `main.js` behaviour (mobile
nav, scroll-spy, back-to-top, preloader, AOS init, flash toast) because the
legacy IIFEs bind to `window load`, already fired by hydration time.

Not visually diffed against the live site yet (browser tooling was unavailable);
markup + CSS are a 1:1 port, needs a screenshot pass.

## Remaining work (dashboard — phase 2)

Per page, the pattern is:

1. **Add a JSON route** in `blueprints/api.py` mirroring the Jinja route's
   `render_template(..., k=v)` context as `jsonify({...})`. Coerce discord
   objects to `str` (see the role/emoji handling in `api.py`).
2. **Build the RSC page** under `frontend/src/app/dashboard/[guildId]/...` that
   `quartJSON()`s that route.
3. **Build the client component** for the interactive bits; mutations `fetch`
   `/api/quart/<existing action route>`.
4. Delete the `.html` template + its inline `<script>` once parity is verified.

### Checklist

- [ ] `meta` endpoint: currently gated by `plugin_guard('economy')` as a
      stand-in — give it a dedicated auth-only guard (perm check, no plugin).
- [ ] Shared shell: navbar, sidebar, guild switcher, notifications bell
      (`context.py` processors → `/api/dashboard/<gid>/meta` is the start).
- [ ] Guild picker (`/dashboard`, `dashboard/guilds.html`).
- [ ] Pages: welcome, moderation, verification, starboard, forms (+create/edit/
      subs), temporary_channels, ticketing, stats, leveling, birthdays,
      giveaways, economy shop polish.
- [ ] Components: **embed editor** and **emoji picker** (the two hard ones),
      premium modal, save-toast, plugin hovercard/disabled modal.
- [ ] Economy: wire the real emoji picker; port the "reset coins / reset shop"
      modals (`EconomyUsers` reset key + `economy.shop: []`).
- [ ] Static pages (index, docs, terms, login, error pages) — decide keep-in-
      Quart vs port.
- [ ] Stripe pages (`premium/index`, `premium/manage`) — checkout/portal
      redirects.
- [ ] Delete `oauth_callback.html` flow + Quart `/oauth/*` once Auth.js is the
      only login path.
- [ ] Deploy: run Next alongside Quart (reverse proxy `/` → Next, `/api` →
      Quart) or as separate services.

## Auth (Auth.js / Discord OAuth) — wired

- `src/auth.ts`: Discord provider, scope `identify guilds`, `trustHost: true`,
  `pages.signIn: "/login"`. JWT callback stores access/refresh tokens and
  transparently refreshes against `https://discord.com/api/oauth2/token` when
  the access token is within 60s of expiry; `session.error` is set if refresh
  fails so the UI can force re-auth.
- `/login` = port of `templates/login.html`; its "Login with Discord" button is
  a server action calling `signIn("discord", { redirectTo })`. `proxy.ts`
  bounces unauthed `/dashboard/*` here with `?callbackUrl=`.
- Navbar: login link → `/login`; logout → `LogoutLink` client component
  (`signOut({ redirectTo: "/" })`), replacing the old `/oauth/logout`.
- Verified locally: `/dashboard/123` → 302 `/login?callbackUrl=%2Fdashboard%2F123`;
  signin POST → correct Discord authorize URL (right client_id, redirect_uri,
  scope, PKCE). Full consent round-trip needs the redirect URI
  `http://localhost:3000/api/auth/callback/discord` registered on the Discord app.
- Quart side already accepts the forwarded Bearer token via
  `utils.current_token()` (header OR legacy session cookie).
