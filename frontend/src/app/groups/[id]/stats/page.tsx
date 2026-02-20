"use client";

import { useParams } from "next/navigation";
import { useCachedFetch } from "@/hooks/use-cached-fetch";
import { getCurrencySymbol } from "@/lib/currency";

interface Stats {
  total_spending: string;
  receipt_count: number;
  base_currency: string;
  spending_by_user: {
    user_id: string;
    display_name: string;
    amount: string;
    paid: string;
    balance: string;
  }[];
}

export default function StatsPage() {
  const params = useParams();
  const groupId = params.id as string;
  const { data: stats, loading } = useCachedFetch<Stats>(`/api/groups/${groupId}/stats`);

  const currencySymbol = stats ? getCurrencySymbol(stats.base_currency) : "$";

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 space-y-6">
      <h1 className="text-2xl font-bold text-stone-900">Statistics</h1>

      {loading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-stone-200" />
          ))}
        </div>
      ) : stats ? (
        <div>
          {/* Summary cards */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl border-l-4 border-l-emerald-600 bg-white p-4 text-center shadow-sm">
              <p className="text-sm text-stone-500">Total Spending</p>
              <p className="mt-1 text-2xl font-bold font-mono text-stone-900">
                {currencySymbol}{stats.total_spending}
              </p>
            </div>
            <div className="rounded-xl border-l-4 border-l-amber-500 bg-white p-4 text-center shadow-sm">
              <p className="text-sm text-stone-500">Receipts</p>
              <p className="mt-1 text-2xl font-bold font-mono text-stone-900">{stats.receipt_count}</p>
            </div>
          </div>

          {/* Per-user breakdown */}
          <section className="mt-6">
            <h2 className="mb-3 text-lg font-semibold text-stone-900">Member Breakdown</h2>
            {stats.spending_by_user.length === 0 ? (
              <p className="text-sm text-stone-500">No spending data yet.</p>
            ) : (
              <div className="space-y-3">
                {stats.spending_by_user.map((u) => {
                  const balance = parseFloat(u.balance);
                  const isPositive = balance > 0;
                  const isNegative = balance < 0;

                  return (
                    <div key={u.user_id} className="rounded-xl border-l-4 border-l-emerald-600 bg-white p-4 shadow-sm">
                      <div className="mb-3">
                        <span className="font-medium text-stone-900">{u.display_name}</span>
                      </div>
                      <div className="grid grid-cols-3 gap-3 text-sm">
                        <div>
                          <p className="text-stone-500 text-xs mb-1">Spent</p>
                          <p className="font-mono font-semibold text-stone-900">{currencySymbol}{u.amount}</p>
                        </div>
                        <div>
                          <p className="text-stone-500 text-xs mb-1">Paid</p>
                          <p className="font-mono font-semibold text-emerald-700">{currencySymbol}{u.paid}</p>
                        </div>
                        <div>
                          <p className="text-stone-500 text-xs mb-1">Balance</p>
                          <p className={`font-mono font-semibold ${
                            isPositive ? "text-emerald-700" :
                            isNegative ? "text-rose-600" :
                            "text-stone-500"
                          }`}>
                            {isPositive && "+"}{currencySymbol}{Math.abs(balance).toFixed(2)}
                          </p>
                        </div>
                      </div>
                      {isPositive && (
                        <p className="mt-2 text-xs text-emerald-700">✓ Owed {currencySymbol}{balance.toFixed(2)} by others</p>
                      )}
                      {isNegative && (
                        <p className="mt-2 text-xs text-rose-600">↓ Owes {currencySymbol}{Math.abs(balance).toFixed(2)}</p>
                      )}
                      {balance === 0 && (
                        <p className="mt-2 text-xs text-stone-500">✓ All settled up</p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}
