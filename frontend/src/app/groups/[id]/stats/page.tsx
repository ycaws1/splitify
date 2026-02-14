"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { AuthGuard } from "@/components/auth-guard";

interface Stats {
  period: string;
  total_spending: string;
  receipt_count: number;
  spending_by_user: { user_id: string; display_name: string; amount: string }[];
}

const periods = [
  { value: "1d", label: "24h" },
  { value: "1mo", label: "30 days" },
  { value: "1yr", label: "1 year" },
];

export default function StatsPage() {
  const params = useParams();
  const groupId = params.id as string;
  const [period, setPeriod] = useState("1mo");
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch(`/api/groups/${groupId}/stats?period=${period}`)
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [groupId, period]);

  const maxAmount = stats
    ? Math.max(...stats.spending_by_user.map((u) => parseFloat(u.amount)), 1)
    : 1;

  return (
    <AuthGuard>
      <div className="mx-auto max-w-2xl px-4 py-6 space-y-6 animate-page">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-stone-900">Statistics</h1>
          <Link href={`/groups/${groupId}`} className="text-sm text-emerald-700 hover:text-emerald-900">
            ← Back
          </Link>
        </div>

        {/* Period selector */}
        <div className="flex gap-2">
          {periods.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
                period === p.value
                  ? "bg-emerald-700 text-white"
                  : "bg-stone-100 text-stone-600 hover:bg-stone-200"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="h-20 animate-pulse rounded-xl bg-stone-200" />
            ))}
          </div>
        ) : stats ? (
          <>
            {/* Summary cards */}
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl border-l-4 border-l-emerald-600 bg-white p-4 text-center shadow-sm">
                <p className="text-sm text-stone-500">Total Spending</p>
                <p className="mt-1 text-2xl font-bold font-mono text-stone-900">${stats.total_spending}</p>
              </div>
              <div className="rounded-xl border-l-4 border-l-amber-500 bg-white p-4 text-center shadow-sm">
                <p className="text-sm text-stone-500">Receipts</p>
                <p className="mt-1 text-2xl font-bold font-mono text-stone-900">{stats.receipt_count}</p>
              </div>
            </div>

            {/* Per-user spending */}
            <section>
              <h2 className="mb-3 text-lg font-semibold text-stone-900">Spending by Member</h2>
              {stats.spending_by_user.length === 0 ? (
                <p className="text-sm text-stone-500">No spending data for this period.</p>
              ) : (
                <div className="space-y-3">
                  {stats.spending_by_user.map((u) => (
                    <div key={u.user_id} className="rounded-xl border-l-4 border-l-emerald-600 bg-white p-4 shadow-sm">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-stone-900">{u.display_name}</span>
                        <span className="font-semibold font-mono text-stone-900">${u.amount}</span>
                      </div>
                      <div className="h-2 rounded-full bg-stone-100 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-emerald-600 transition-all"
                          style={{ width: `${(parseFloat(u.amount) / maxAmount) * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        ) : null}
      </div>
    </AuthGuard>
  );
}
