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
      <div className="mx-auto max-w-2xl px-4 py-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Statistics</h1>
          <Link href={`/groups/${groupId}`} className="text-sm text-indigo-600 hover:text-indigo-800">
            ← Back
          </Link>
        </div>

        {/* Period selector */}
        <div className="flex gap-2">
          {periods.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                period === p.value
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {loading ? (
          <p className="text-gray-500">Loading stats...</p>
        ) : stats ? (
          <>
            {/* Summary cards */}
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg border bg-white p-4 text-center">
                <p className="text-sm text-gray-500">Total Spending</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">${stats.total_spending}</p>
              </div>
              <div className="rounded-lg border bg-white p-4 text-center">
                <p className="text-sm text-gray-500">Receipts</p>
                <p className="mt-1 text-2xl font-bold text-gray-900">{stats.receipt_count}</p>
              </div>
            </div>

            {/* Per-user spending */}
            <section>
              <h2 className="mb-3 text-lg font-semibold text-gray-900">Spending by Member</h2>
              {stats.spending_by_user.length === 0 ? (
                <p className="text-sm text-gray-500">No spending data for this period.</p>
              ) : (
                <div className="space-y-3">
                  {stats.spending_by_user.map((u) => (
                    <div key={u.user_id} className="rounded-lg border bg-white p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-gray-900">{u.display_name}</span>
                        <span className="font-semibold text-gray-900">${u.amount}</span>
                      </div>
                      <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-indigo-600 transition-all"
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
