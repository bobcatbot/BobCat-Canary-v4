"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

export type ShopItem = {
  name: string;
  price: number;
  icon: string;
  description: string;
  type: "string" | "role";
  max_limit: number;
};

export type EconomyPayload = {
  data: {
    status?: boolean;
    icon?: string;
    name?: string;
    MaxGambling?: number | string;
    MaxPayment?: number | string;
    shop?: ShopItem[];
    num_items: number;
  };
  is_premium: boolean;
  shop_cap: number;
  shop_cap_premium: number;
};

async function postSetting(guildId: string, body: Record<string, unknown>) {
  const res = await fetch(`/api/quart/dashboard/${guildId}/data/post`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = await res.json().catch(() => null);
  if (!res.ok || json?.status === "error") {
    throw new Error(json?.message ?? `Request failed (HTTP ${res.status})`);
  }
  return json;
}

const BLANK: ShopItem = {
  name: "",
  price: 100,
  icon: "😊",
  description: "",
  type: "string",
  max_limit: 5,
};

export function EconomyForm({
  guildId,
  initial,
}: {
  guildId: string;
  initial: EconomyPayload;
}) {
  const d = initial.data;
  const [status, setStatus] = useState(Boolean(d.status));
  const [name, setName] = useState(d.name ?? "BobCat Coin");
  const [icon, setIcon] = useState(d.icon ?? "🪙");
  const [maxGambling, setMaxGambling] = useState(String(d.MaxGambling ?? ""));
  const [maxPayment, setMaxPayment] = useState(String(d.MaxPayment ?? ""));
  const [shop, setShop] = useState<ShopItem[]>(d.shop ?? []);
  const [editing, setEditing] = useState<ShopItem | null>(null);
  const [editIdx, setEditIdx] = useState<number | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: (body: Record<string, unknown>) => postSetting(guildId, body),
    onError: (e: Error) => setMsg(e.message),
    onSuccess: () => setMsg("Saved"),
  });

  const atCap = shop.length >= initial.shop_cap;

  function commitShop(next: ShopItem[]) {
    setShop(next);
    save.mutate({ "economy.shop": next });
  }

  return (
    <div className="space-y-8">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Economy</h1>
          <p className="text-sm text-neutral-500">
            Players earn coins daily, stake them in games, and spend them in the
            shop.
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={status}
            onChange={(e) => {
              setStatus(e.target.checked);
              save.mutate({ "economy.status": e.target.checked });
            }}
          />
          {status ? "Enabled" : "Disabled"}
        </label>
      </header>

      {msg && (
        <p className="rounded bg-neutral-100 px-3 py-2 text-sm">{msg}</p>
      )}

      <section className="space-y-3 rounded-lg border p-4">
        <h2 className="font-medium">Currency</h2>
        <div className="flex gap-4">
          <input
            className="w-16 rounded border text-center text-2xl"
            value={icon}
            onChange={(e) => setIcon(e.target.value)}
            onBlur={() =>
              icon !== d.icon && save.mutate({ "economy.icon": icon })
            }
            aria-label="Currency icon"
          />
          <label className="flex flex-1 flex-col gap-1 text-sm">
            Currency name
            <input
              className="rounded border px-2 py-1"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onBlur={() =>
                name !== d.name && save.mutate({ "economy.name": name })
              }
            />
          </label>
        </div>
      </section>

      <section className="space-y-3 rounded-lg border p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-medium">Items</h2>
          <span className="text-xs text-neutral-500">
            {shop.length} / {initial.shop_cap}
          </span>
        </div>
        <ul className="space-y-2">
          {shop.map((item, i) => (
            <li
              key={i}
              className="flex items-center justify-between rounded border px-3 py-2 text-sm"
            >
              <span>
                {item.icon} {item.name} — {item.price} {icon} (max{" "}
                {item.max_limit})
              </span>
              <span className="flex gap-2">
                <button
                  className="text-indigo-600"
                  onClick={() => {
                    setEditing({ ...item });
                    setEditIdx(i);
                  }}
                >
                  edit
                </button>
                <button
                  className="text-red-600"
                  onClick={() =>
                    commitShop(shop.filter((_, j) => j !== i))
                  }
                >
                  delete
                </button>
              </span>
            </li>
          ))}
        </ul>
        <button
          className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white disabled:opacity-40"
          disabled={atCap}
          onClick={() => {
            setEditing({ ...BLANK });
            setEditIdx(null);
          }}
        >
          Add item
        </button>
      </section>

      <section className="grid gap-4 rounded-lg border p-4 sm:grid-cols-2">
        <h2 className="font-medium sm:col-span-2">Restrictions</h2>
        <label className="flex flex-col gap-1 text-sm">
          Max gambling
          <input
            className="rounded border px-2 py-1"
            value={maxGambling}
            onChange={(e) => setMaxGambling(e.target.value)}
            onBlur={() =>
              save.mutate({ "economy.MaxGambling": maxGambling })
            }
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Max payment
          <input
            className="rounded border px-2 py-1"
            value={maxPayment}
            onChange={(e) => setMaxPayment(e.target.value)}
            onBlur={() =>
              save.mutate({ "economy.MaxPayment": maxPayment })
            }
          />
        </label>
      </section>

      {editing && (
        <ItemDialog
          item={editing}
          onCancel={() => setEditing(null)}
          onSave={(item) => {
            const next =
              editIdx === null
                ? [...shop, item]
                : shop.map((it, j) => (j === editIdx ? item : it));
            setEditing(null);
            commitShop(next);
          }}
        />
      )}
    </div>
  );
}

function ItemDialog({
  item,
  onCancel,
  onSave,
}: {
  item: ShopItem;
  onCancel: () => void;
  onSave: (item: ShopItem) => void;
}) {
  const [draft, setDraft] = useState<ShopItem>(item);
  const set = <K extends keyof ShopItem>(k: K, v: ShopItem[K]) =>
    setDraft((p) => ({ ...p, [k]: v }));

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm space-y-3 rounded-lg bg-white p-4">
        <h3 className="font-medium">
          {item.name ? "Edit shop item" : "Create shop item"}
        </h3>
        <input
          className="w-full rounded border px-2 py-1 text-sm"
          placeholder="Name"
          value={draft.name}
          onChange={(e) => set("name", e.target.value)}
        />
        <input
          className="w-full rounded border px-2 py-1 text-sm"
          placeholder="Price"
          type="number"
          value={draft.price}
          onChange={(e) => set("price", Number(e.target.value))}
        />
        <input
          className="w-full rounded border px-2 py-1 text-sm"
          placeholder="Icon"
          value={draft.icon}
          onChange={(e) => set("icon", e.target.value)}
        />
        <textarea
          className="w-full rounded border px-2 py-1 text-sm"
          placeholder="Description"
          value={draft.description}
          onChange={(e) => set("description", e.target.value)}
        />
        <select
          className="w-full rounded border px-2 py-1 text-sm"
          value={draft.type}
          onChange={(e) => set("type", e.target.value as ShopItem["type"])}
        >
          <option value="string">Useable item</option>
          <option value="role">Role</option>
        </select>
        <input
          className="w-full rounded border px-2 py-1 text-sm"
          placeholder="Max per player"
          type="number"
          value={draft.max_limit}
          onChange={(e) => set("max_limit", Number(e.target.value))}
        />
        <div className="flex justify-end gap-2 text-sm">
          <button className="px-3 py-1" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="rounded bg-indigo-600 px-3 py-1 text-white disabled:opacity-40"
            disabled={!draft.name.trim() || draft.price <= 0}
            onClick={() => onSave(draft)}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
