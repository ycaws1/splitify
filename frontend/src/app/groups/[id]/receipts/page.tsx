"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { getCurrencySymbol } from "@/lib/currency";
import type { Group } from "@/types";

interface ReceiptSummary {
  id: string;
  merchant_name: string | null;
  total: string | null;
  currency: string;
  exchange_rate: string;
  status: string;
  created_at: string;
}

export default function ReceiptListPage() {
  const params = useParams();
  const groupId = params.id as string;
  const [receipts, setReceipts] = useState<ReceiptSummary[]>([]);
  const [group, setGroup] = useState<Group | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    apiFetch(`/api/groups/${groupId}`).then(setGroup).catch(console.error);
  }, [groupId]);

  useEffect(() => {
    let stale = false;
    const load = () => {
      apiFetch(`/api/groups/${groupId}/receipts`)
        .then((data) => { if (!stale) setReceipts(data); })
        .catch(console.error)
        .finally(() => { if (!stale) setLoading(false); });
    };
    load();
    // Refetch when user returns to this tab/page
    const onVisible = () => { if (document.visibilityState === "visible") load(); };
    const onFocus = () => load();
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", onFocus);
    return () => {
      stale = true;
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", onFocus);
    };
  }, [groupId]);

  const handleDelete = async (e: React.MouseEvent, receiptId: string) => {
    e.preventDefault(); // Prevent navigation
    e.stopPropagation();

    if (!confirm("Delete this receipt?")) return;

    setDeleting(receiptId);
    try {
      await apiFetch(`/api/receipts/${receiptId}`, { method: "DELETE" });
      setReceipts(receipts.filter(r => r.id !== receiptId));
    } catch (error) {
      console.error("Failed to delete receipt:", error);
      alert("Failed to delete receipt");
    } finally {
      setDeleting(null);
    }
  };

  const statusColors: Record<string, string> = {
    processing: "bg-amber-100 text-amber-800",
    extracted: "bg-sky-100 text-sky-800",
    confirmed: "bg-emerald-100 text-emerald-800",
    failed: "bg-rose-100 text-rose-800",
  };

  const borderColors: Record<string, string> = {
    processing: "border-l-amber-500",
    extracted: "border-l-sky-500",
    confirmed: "border-l-emerald-600",
    failed: "border-l-rose-500",
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-stone-900">Receipts</h1>
        <Link
          href={`/groups/${groupId}/receipts/new`}
          className="rounded-xl bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
        >
          Upload Receipt
        </Link>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-stone-200" />
          ))}
        </div>
      ) : receipts.length === 0 ? (
        <div className="rounded-2xl border-2 border-dashed border-stone-300 p-12 text-center">
          <p className="text-stone-500">No receipts yet. Upload one to get started!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {receipts.map((r) => (
            <Link
              key={r.id}
              href={`/receipts/${r.id}`}
              className={`block rounded-xl border-l-4 ${borderColors[r.status] || "border-l-stone-300"} bg-white p-4 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5 relative group`}
            >
              {/* Delete button - shows on hover */}
              <button
                onClick={(e) => handleDelete(e, r.id)}
                disabled={deleting === r.id}
                className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-rose-500 text-white hover:bg-rose-600 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-sm font-bold shadow-md disabled:opacity-50"
                title="Delete receipt"
              >
                ×
              </button>

              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-semibold text-stone-900">
                    {r.merchant_name || "Processing..."}
                  </h2>
                  <p className="mt-1 text-sm text-stone-500">
                    {new Date(r.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="text-right">
                  {r.total && (
                    <>
                      <p className="font-semibold font-mono text-stone-900">
                        {getCurrencySymbol(r.currency)}{r.total}
                      </p>
                      {group && r.currency !== group.base_currency && (
                        <p className="text-xs font-mono text-stone-400">
                          {getCurrencySymbol(group.base_currency)}{(parseFloat(r.total) * parseFloat(r.exchange_rate)).toFixed(2)}
                        </p>
                      )}
                    </>
                  )}
                  <span
                    className={`inline-block mt-1 rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[r.status] || "bg-stone-100 text-stone-800"}`}
                  >
                    {r.status}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
