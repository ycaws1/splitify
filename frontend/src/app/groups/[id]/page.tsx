"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";
import { apiFetch } from "@/lib/api";
import { AuthGuard } from "@/components/auth-guard";
import type { Group, BalanceEntry } from "@/types";

export default function GroupDetailPage() {
  const params = useParams();
  const groupId = params.id as string;
  const [group, setGroup] = useState<Group | null>(null);
  const [balances, setBalances] = useState<BalanceEntry[]>([]);
  const [showInvite, setShowInvite] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiFetch(`/api/groups/${groupId}`),
      apiFetch(`/api/groups/${groupId}/balances`),
    ])
      .then(([g, b]) => {
        setGroup(g);
        setBalances(b.balances);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [groupId]);

  if (loading) return <AuthGuard><p className="p-6 text-stone-500">Loading...</p></AuthGuard>;
  if (!group) return <AuthGuard><p className="p-6 text-rose-500">Group not found</p></AuthGuard>;

  const inviteUrl = typeof window !== "undefined"
    ? `${window.location.origin}/join/${group.invite_code}`
    : "";

  return (
    <AuthGuard>
      <div className="mx-auto max-w-2xl px-4 py-6 space-y-6 animate-page">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-stone-900">{group.name}</h1>
          <Link
            href={`/groups/${groupId}/receipts`}
            className="rounded-xl bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
          >
            Receipts
          </Link>
        </div>

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
          {balances.length === 0 ? (
            <p className="text-stone-500 text-sm">All settled up!</p>
          ) : (
            <div className="space-y-2">
              {balances.map((b, i) => (
                <div key={i} className="flex items-center justify-between rounded-xl border-l-4 border-l-emerald-600 bg-white px-4 py-3 shadow-sm">
                  <span className="text-sm text-stone-700">
                    <span className="font-medium">{b.from_user_name}</span> owes{" "}
                    <span className="font-medium">{b.to_user_name}</span>
                  </span>
                  <span className="font-semibold font-mono text-rose-600">${b.amount}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </AuthGuard>
  );
}
