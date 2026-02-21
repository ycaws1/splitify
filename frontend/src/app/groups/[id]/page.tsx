"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useCachedFetch, invalidateCache } from "@/hooks/use-cached-fetch";

const QRCodeSVG = dynamic(
  () => import("qrcode.react").then((mod) => mod.QRCodeSVG),
  { loading: () => <div className="h-[160px] w-[160px] animate-pulse rounded bg-stone-200" /> }
);
import { apiFetch } from "@/lib/api";
import { getCurrencySymbol, COMMON_CURRENCIES } from "@/lib/currency";
import type { Group, BalanceEntry } from "@/types";

export default function GroupDetailPage() {
  const params = useParams();
  const router = useRouter();
  const groupId = params.id as string;
  const [group, setGroup] = useState<Group | null>(null);
  const [balances, setBalances] = useState<BalanceEntry[]>([]);
  const [totalAssigned, setTotalAssigned] = useState("0");
  const [totalPaid, setTotalPaid] = useState("0");
  // Loading state handled by useCachedFetch
  const [showInvite, setShowInvite] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [settling, setSettling] = useState<string | null>(null);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editName, setEditName] = useState("");

  const handleSettle = async (b: BalanceEntry) => {
    const sym = group ? getCurrencySymbol(group.base_currency) : "$";
    if (!confirm(`Mark ${b.from_user_name}'s debt of ${sym}${b.amount} to ${b.to_user_name} as settled?`)) return;
    const key = `${b.from_user_id}-${b.to_user_id}`;
    setSettling(key);
    try {
      await apiFetch(`/api/groups/${groupId}/settle`, {
        method: "POST",
        body: JSON.stringify({
          from_user: b.from_user_id,
          to_user: b.to_user_id,
          amount: parseFloat(b.amount),
        }),
      });
      // Refresh balances (invalidate cache first to ensure fresh data)
      invalidateCache(`/api/groups/${groupId}`);
      const updated = await apiFetch(`/api/groups/${groupId}/balances`);
      setBalances(updated.balances);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to settle");
    } finally {
      setSettling(null);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this group? This cannot be undone.")) return;
    setDeleting(true);
    try {
      await apiFetch(`/api/groups/${groupId}`, { method: "DELETE" });
      router.push("/dashboard");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete group");
      setDeleting(false);
    }
  };

  const { data: groupData, loading: groupLoading, isValidating } = useCachedFetch<Group & { balances: BalanceEntry[]; total_assigned: string; total_paid: string }>(`/api/groups/${groupId}?include=balances`);

  // Removed local loading state logic in favor of using groupLoading directly
  useEffect(() => {
    if (groupData) {
      setGroup(groupData);
      setBalances(groupData.balances ?? []);
      setTotalAssigned(groupData.total_assigned ?? "0");
      setTotalPaid(groupData.total_paid ?? "0");
    }
  }, [groupData]);

  if (groupLoading) return (
    <div className="mx-auto max-w-2xl px-4 py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="h-8 w-40 animate-pulse rounded-lg bg-stone-200" />
        <div className="h-10 w-24 animate-pulse rounded-xl bg-stone-200" />
      </div>
      <div className="h-20 animate-pulse rounded-2xl bg-stone-200" />
      <div className="space-y-2">
        <div className="h-6 w-28 animate-pulse rounded bg-stone-200" />
        {[1, 2].map((i) => (
          <div key={i} className="h-14 animate-pulse rounded-xl bg-stone-200" />
        ))}
      </div>
    </div>
  );
  if (!group) return <p className="p-6 text-rose-500">Group not found</p>;

  const inviteUrl = typeof window !== "undefined"
    ? `${window.location.origin}/join/${group.invite_code}`
    : "";

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 space-y-6">
      <div className="flex items-center justify-between">
        {isEditingName ? (
          <form
            className="flex items-center gap-2"
            onSubmit={async (e) => {
              e.preventDefault();
              const trimmed = editName.trim();
              if (!trimmed || trimmed === group.name) {
                setIsEditingName(false);
                return;
              }
              try {
                const updated = await apiFetch(`/api/groups/${groupId}`, {
                  method: "PUT",
                  body: JSON.stringify({ name: trimmed }),
                });
                setGroup(updated);
                setIsEditingName(false);
              } catch (err: unknown) {
                alert(err instanceof Error ? err.message : "Failed to rename group");
              }
            }}
          >
            <input
              autoFocus
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="rounded-lg border border-stone-300 px-2 py-1 text-2xl font-bold text-stone-900 focus:border-emerald-600 focus:outline-none"
            />
            <button type="submit" className="rounded-lg bg-emerald-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-800">
              Save
            </button>
            <button type="button" onClick={() => setIsEditingName(false)} className="rounded-lg px-3 py-1.5 text-sm font-medium text-stone-500 hover:bg-stone-100">
              Cancel
            </button>
          </form>
        ) : (
          <div className="flex items-center gap-2">
            <h1
              className="text-2xl font-bold text-stone-900 cursor-pointer hover:text-emerald-800 transition-colors"
              onClick={() => { setEditName(group.name); setIsEditingName(true); }}
              title="Click to rename"
            >
              {group.name}
            </h1>
            {isValidating && (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" title="Refreshing data..." />
            )}
          </div>
        )}
        <Link
          href={`/groups/${groupId}/receipts`}
          className="rounded-xl bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
        >
          Receipts
        </Link>
      </div>

      {/* Base Currency */}
      <section className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-stone-900">Base Currency</h2>
            <p className="text-xs text-stone-400">All balances are shown in this currency</p>
          </div>
          <select
            value={group.base_currency}
            onChange={async (e) => {
              const newCurrency = e.target.value;
              try {
                const updated = await apiFetch(`/api/groups/${groupId}`, {
                  method: "PUT",
                  body: JSON.stringify({ base_currency: newCurrency }),
                });
                setGroup(updated);
                const b = await apiFetch(`/api/groups/${groupId}/balances`);
                setBalances(b.balances);
                setTotalAssigned(b.total_assigned || "0");
                setTotalPaid(b.total_paid || "0");
              } catch (err: unknown) {
                alert(err instanceof Error ? err.message : "Failed to update currency");
              }
            }}
            className="rounded-xl border border-stone-300 px-3 py-2 text-sm focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
          >
            {COMMON_CURRENCIES.map((c) => (
              <option key={c} value={c}>{c} ({getCurrencySymbol(c)})</option>
            ))}
          </select>
        </div>
      </section>

      {/* Members */}
      <section>
        <h2 className="mb-3 text-lg font-semibold text-stone-900">Members ({group.members.length})</h2>
        <div className="space-y-2">
          {group.members.map((m) => (
            <div key={m.user_id} className="flex items-center justify-between rounded-xl border-l-4 border-l-emerald-600 bg-white px-4 py-3 shadow-sm">
              <span className="text-stone-900">{m.display_name || "Unknown"}</span>
              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">{m.role}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Invite */}
      <section>
        <button
          onClick={() => setShowInvite(!showInvite)}
          className="w-full rounded-xl border-2 border-emerald-700 px-4 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50"
        >
          {showInvite ? "Hide Invite" : "Invite Members"}
        </button>
        {showInvite && (
          <div className="mt-4 rounded-xl border border-stone-200 bg-white p-4 text-center space-y-3 shadow-sm">
            <p className="text-sm text-stone-500">Share this code or scan the QR:</p>
            <p className="text-2xl font-mono font-bold tracking-wider text-stone-900">{group.invite_code}</p>
            <div className="flex justify-center">
              <QRCodeSVG value={inviteUrl} size={160} />
            </div>
            <button
              onClick={() => navigator.clipboard.writeText(inviteUrl)}
              className="text-sm text-emerald-700 hover:text-emerald-900"
            >
              Copy invite link
            </button>
          </div>
        )}
      </section>

      {/* Balances */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-stone-900">Balances</h2>
          <Link href={`/groups/${groupId}/stats`} className="text-sm text-emerald-700 hover:text-emerald-900">
            View Stats
          </Link>
        </div>
        {balances.length === 0 && parseFloat(totalAssigned) > 0 && parseFloat(totalPaid) === 0 ? (
          <div className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
            <p className="font-medium">Payments not recorded yet</p>
            <p className="mt-1">Items assigned totalling <span className="font-mono font-semibold">{getCurrencySymbol(group.base_currency)}{totalAssigned}</span> but no one has recorded who paid. Go to each receipt and record payments.</p>
          </div>
        ) : balances.length === 0 ? (
          <p className="text-stone-500 text-sm">All settled up!</p>
        ) : (
          <div className="space-y-2">
            {balances.map((b, i) => {
              const key = `${b.from_user_id}-${b.to_user_id}`;
              return (
                <div key={i} className="flex items-center justify-between rounded-xl border-l-4 border-l-emerald-600 bg-white px-4 py-3 shadow-sm">
                  <div>
                    <span className="text-sm text-stone-700">
                      <span className="font-medium">{b.from_user_name}</span> owes{" "}
                      <span className="font-medium">{b.to_user_name}</span>
                    </span>
                    <span className="ml-2 font-semibold font-mono text-rose-600">{getCurrencySymbol(group.base_currency)}{b.amount}</span>
                  </div>
                  <button
                    onClick={() => handleSettle(b)}
                    disabled={settling === key}
                    className="rounded-lg bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
                  >
                    {settling === key ? "..." : "Settle"}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Danger zone */}
      <section className="pt-4 border-t border-stone-200 space-y-2">
        <button
          onClick={async () => {
            if (!confirm("Reset all receipts, payments, and settlements for this group?")) return;
            try {
              const result = await apiFetch(`/api/groups/${groupId}/reset`, { method: "DELETE" });
              alert(`Deleted ${result.receipts_deleted} receipts and ${result.settlements_deleted} settlements`);
              const updated = await apiFetch(`/api/groups/${groupId}/balances`);
              setBalances(updated.balances);
            } catch (err: unknown) {
              alert(err instanceof Error ? err.message : "Failed to reset");
            }
          }}
          className="w-full rounded-xl border-2 border-amber-300 px-4 py-2 text-sm font-medium text-amber-600 hover:bg-amber-50"
        >
          Reset Group Data
        </button>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="w-full rounded-xl border-2 border-rose-300 px-4 py-2 text-sm font-medium text-rose-600 hover:bg-rose-50 disabled:opacity-50"
        >
          {deleting ? "Deleting..." : "Delete Group"}
        </button>
      </section>
    </div>
  );
}
