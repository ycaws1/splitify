"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { AuthGuard } from "@/components/auth-guard";

interface ReceiptSummary {
  id: string;
  merchant_name: string | null;
  total: string | null;
  status: string;
  created_at: string;
}

export default function ReceiptListPage() {
  const params = useParams();
  const groupId = params.id as string;
  const [receipts, setReceipts] = useState<ReceiptSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch(`/api/groups/${groupId}/receipts`)
      .then(setReceipts)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [groupId]);

  const statusColors: Record<string, string> = {
    processing: "bg-amber-100 text-amber-800",
    extracted: "bg-sky-100 text-sky-800",
    confirmed: "bg-emerald-100 text-emerald-800",
  };

  const borderColors: Record<string, string> = {
    processing: "border-l-amber-500",
    extracted: "border-l-sky-500",
    confirmed: "border-l-emerald-600",
  };

  return (
    <AuthGuard>
      <div className="mx-auto max-w-2xl px-4 py-6 animate-page">
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
                className={`block rounded-xl border-l-4 ${borderColors[r.status] || "border-l-stone-300"} bg-white p-4 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5`}
              >
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
                    {r.total && <p className="font-semibold font-mono text-stone-900">${r.total}</p>}
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

        <div className="mt-6">
          <Link href={`/groups/${groupId}`} className="text-sm text-emerald-700 hover:text-emerald-900">
            &larr; Back to group
          </Link>
        </div>
      </div>
    </AuthGuard>
  );
}
