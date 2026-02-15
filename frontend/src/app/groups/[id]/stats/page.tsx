"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { getCurrencySymbol } from "@/lib/currency";

interface Stats {
  period: string;
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
  const [initialLoading, setInitialLoading] = useState(true);
  const [switching, setSwitching] = useState(false);
  const cache = useRef<Record<string, Stats>>({});

  const currencySymbol = stats ? getCurrencySymbol(stats.base_currency) : "$";

  useEffect(() => {
    // Use cached data if available
    if (cache.current[period]) {
      setStats(cache.current[period]);
      setInitialLoading(false);
      return;
    }

    setSwitching(true);
    apiFetch(`/api/groups/${groupId}/stats?period=${period}`)
      .then((data) => {
        cache.current[period] = data;
        setStats(data);
      })
      .catch(console.error)
      .finally(() => {
        setInitialLoading(false);
        setSwitching(false);
      });
  }, [groupId, period]);

  const maxAmount = stats
    ? Math.max(...stats.spending_by_user.map((u) => parseFloat(u.amount)), 1)
    : 1;

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-stone-900">Statistics</h1>
      </div>

      {/* Period selector */}
      <div className="flex gap-2">
        {periods.map((p) => (
          <button
            key={p.value}
            onClick={() => setPeriod(p.value)}
            className={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${period === p.value
              ? "bg-emerald-700 text-white"
              : "bg-stone-100 text-stone-600 hover:bg-stone-200"
              }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {initialLoading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-stone-200" />
          ))}
        </div>
      ) : stats ? (
        <div className={switching ? "opacity-50 transition-opacity" : "transition-opacity"}>
          {/* Summary cards */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl border-l-4 border-l-emerald-600 bg-white p-4 text-center shadow-sm">
              <p className="text-sm text-stone-500">Total Spending</p>
              <p className="mt-1 text-2xl font-bold font-mono text-stone-900">{currencySymbol}{stats.total_spending}</p>
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
              <p className="text-sm text-stone-500">No spending data for this period.</p>
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

                      {/* Financial details */}
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
                          <p className={`font-mono font-semibold ${isPositive ? "text-emerald-700" :
                            isNegative ? "text-rose-600" :
                              "text-stone-500"
                            }`}>
                            {isPositive && "+"}{currencySymbol}{Math.abs(balance).toFixed(2)}
                          </p>
                        </div>
                      </div>

                      {/* Balance explanation */}
                      {isPositive && (
                        <p className="mt-2 text-xs text-emerald-700">
                          ✓ Owed {currencySymbol}{balance.toFixed(2)} by others
                        </p>
                      )}
                      {isNegative && (
                        <p className="mt-2 text-xs text-rose-600">
                          ↓ Owes {currencySymbol}{Math.abs(balance).toFixed(2)}
                        </p>
                      )}
                      {balance === 0 && (
                        <p className="mt-2 text-xs text-stone-500">
                          ✓ All settled up
                        </p>
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
