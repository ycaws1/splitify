"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useCachedFetch, invalidateCache } from "@/hooks/use-cached-fetch";
import { apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
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

  // Fetch group data separately for currency info
  const { data: groupData } = useCachedFetch<Group>(`/api/groups/${groupId}`);

  // Fetch receipts list
  const {
    data: receiptsData,
    loading: receiptsLoading,
    refetch: refetchReceipts,
    setData: setReceiptsData
  } = useCachedFetch<any>(`/api/groups/${groupId}/receipts`);

  const [receipts, setReceipts] = useState<ReceiptSummary[]>(
    receiptsData ? (Array.isArray(receiptsData) ? receiptsData : receiptsData.receipts || []) : []
  );
  const [group, setGroup] = useState<Group | null>(groupData || null);
  const [loading, setLoading] = useState(!receiptsData);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Track optimistically deleted IDs to prevent them from reappearing if cache is stale
  const deletedReceiptIds = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (groupData) setGroup(groupData);
  }, [groupData]);

  // When fresh data comes from cache/server, update state (but filter out locally deleted ones)
  useEffect(() => {
    if (receiptsData) {
      const rawList = Array.isArray(receiptsData) ? receiptsData : receiptsData.receipts || [];
      const filteredList = rawList.filter((r: ReceiptSummary) => !deletedReceiptIds.current.has(r.id));
      setReceipts(filteredList);
      setLoading(false);
    } else if (receiptsLoading) {
      // Keep existing receipts if refreshing, but if initial load (no data), show loading
      if (receipts.length === 0) setLoading(true);
    }
  }, [receiptsData, receiptsLoading]);

  // Realtime updates
  useEffect(() => {
    const supabase = createClient();
    const channel = supabase
      .channel(`group-receipts-${groupId}`)
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "receipts", filter: `group_id=eq.${groupId}` },
        (payload: any) => {
          console.log("Realtime update received:", payload);
          // Immediate update for better responsiveness
          if (payload.eventType === "UPDATE" && payload.new) {
            setReceipts((prev) =>
              prev.map((r) => r.id === payload.new.id ? { ...r, ...payload.new } : r)
            );
          } else if (payload.eventType === "INSERT" && payload.new) {
            setReceipts((prev) => [payload.new, ...prev]);
          } else if (payload.eventType === "DELETE" && payload.old) {
            setReceipts((prev) => prev.filter((r) => r.id !== payload.old.id));
          }
          refetchReceipts();
        }
      )
      .subscribe((status: string) => {
        console.log("Realtime subscription status:", status);
      });

    return () => {
      supabase.removeChannel(channel);
    };
  }, [groupId, refetchReceipts]);

  // Polling fallback
  useEffect(() => {
    const hasProcessing = receipts.some(r => r.status === "processing");
    if (!hasProcessing) return;

    const interval = setInterval(() => {
      console.log("Polling for updates...");
      refetchReceipts();
    }, 4000);

    return () => clearInterval(interval);
  }, [receipts, refetchReceipts]);

  const handleDelete = async (e: React.MouseEvent, receiptId: string) => {
    e.preventDefault(); // Prevent navigation
    e.stopPropagation();

    if (!confirm("Delete this receipt?")) return;

    // Optimistic: remove from UI immediately
    const previousReceipts = receipts;
    const newReceipts = receipts.filter(r => r.id !== receiptId);
    setReceipts(newReceipts);
    deletedReceiptIds.current.add(receiptId);

    // Also update the cached data source so useEffect doesn't revert it if it runs
    if (receiptsData) {
      if (Array.isArray(receiptsData)) {
        setReceiptsData(newReceipts);
      } else {
        setReceiptsData({ ...receiptsData, receipts: newReceipts });
      }
    }

    try {
      await apiFetch(`/api/receipts/${receiptId}`, { method: "DELETE" });
      invalidateCache(`/api/groups/${groupId}`);
    } catch (error) {
      console.error("Failed to delete receipt:", error);
      alert("Failed to delete receipt");
      // Rollback
      setReceipts(previousReceipts);
      if (receiptsData) setReceiptsData(receiptsData);
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
                className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-rose-500 text-white hover:bg-rose-600 flex items-center justify-center text-sm font-bold shadow-md disabled:opacity-50"
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
