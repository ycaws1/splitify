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
    processing: "bg-yellow-100 text-yellow-800",
    extracted: "bg-blue-100 text-blue-800",
    confirmed: "bg-green-100 text-green-800",
  };

  return (
    <AuthGuard>
      <div className="mx-auto max-w-2xl px-4 py-6">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Receipts</h1>
          <Link
            href={`/groups/${groupId}/receipts/new`}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Upload Receipt
          </Link>
        </div>

        {loading ? (
          <p className="text-gray-500">Loading receipts...</p>
        ) : receipts.length === 0 ? (
          <div className="rounded-lg border-2 border-dashed border-gray-200 p-12 text-center">
            <p className="text-gray-500">No receipts yet. Upload one to get started!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {receipts.map((r) => (
              <Link
                key={r.id}
                href={`/receipts/${r.id}`}
                className="block rounded-lg border bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="font-semibold text-gray-900">
                      {r.merchant_name || "Processing..."}
                    </h2>
                    <p className="mt-1 text-sm text-gray-500">
                      {new Date(r.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="text-right">
                    {r.total && <p className="font-semibold text-gray-900">${r.total}</p>}
                    <span
                      className={`inline-block mt-1 rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[r.status] || "bg-gray-100 text-gray-800"}`}
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
          <Link href={`/groups/${groupId}`} className="text-sm text-indigo-600 hover:text-indigo-800">
            &larr; Back to group
          </Link>
        </div>
      </div>
    </AuthGuard>
  );
}
