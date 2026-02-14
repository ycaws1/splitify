"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { AuthGuard } from "@/components/auth-guard";
import type { Receipt, Assignment, GroupMember } from "@/types";

export default function ReceiptDetailPage() {
  const params = useParams();
  const receiptId = params.id as string;
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [payAmount, setPayAmount] = useState("");
  const [payUserId, setPayUserId] = useState("");

  const fetchReceipt = useCallback(async () => {
    try {
      const r = await apiFetch(`/api/receipts/${receiptId}`);
      setReceipt(r);

      const a = await apiFetch(`/api/receipts/${receiptId}/assignments`);
      setAssignments(a);

      // Fetch group members
      const g = await apiFetch(`/api/groups/${r.group_id}`);
      setMembers(g.members);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [receiptId]);

  useEffect(() => {
    fetchReceipt();
  }, [fetchReceipt]);

  // Realtime subscription for receipt updates
  useEffect(() => {
    const supabase = createClient();
    const channel = supabase
      .channel(`receipt-${receiptId}`)
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "receipts", filter: `id=eq.${receiptId}` },
        () => fetchReceipt()
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [receiptId, fetchReceipt]);

  // Check if a user is assigned to a line item
  const isAssigned = (lineItemId: string, userId: string) => {
    return assignments.some((a) => a.line_item_id === lineItemId && a.user_id === userId);
  };

  // Toggle assignment for a user on a line item
  const toggleAssignment = async (lineItemId: string, userId: string) => {
    if (!receipt) return;
    setSaving(true);

    // Build new assignments for ALL line items
    const newAssignments = receipt.line_items.map((li) => {
      const currentUsers = assignments
        .filter((a) => a.line_item_id === li.id)
        .map((a) => a.user_id);

      let updatedUsers: string[];
      if (li.id === lineItemId) {
        if (currentUsers.includes(userId)) {
          updatedUsers = currentUsers.filter((id) => id !== userId);
        } else {
          updatedUsers = [...currentUsers, userId];
        }
      } else {
        updatedUsers = currentUsers;
      }

      return { line_item_id: li.id, user_ids: updatedUsers };
    });

    try {
      const result = await apiFetch(`/api/receipts/${receiptId}/assignments`, {
        method: "PUT",
        body: JSON.stringify({
          assignments: newAssignments,
          version: receipt.version,
        }),
      });
      setAssignments(result);
      // Refetch receipt for updated version
      const r = await apiFetch(`/api/receipts/${receiptId}`);
      setReceipt(r);
    } catch (err: unknown) {
      if (err instanceof Error && err.message.includes("Version conflict")) {
        await fetchReceipt(); // Refetch on conflict
      }
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  // Record payment
  const handlePayment = async () => {
    if (!payUserId || !payAmount) return;
    try {
      await apiFetch(`/api/receipts/${receiptId}/payments`, {
        method: "POST",
        body: JSON.stringify({
          paid_by: payUserId,
          amount: parseFloat(payAmount),
        }),
      });
      setPayAmount("");
      setPayUserId("");
      alert("Payment recorded!");
    } catch (err) {
      console.error(err);
    }
  };

  if (loading)
    return (
      <AuthGuard>
        <div className="flex h-screen flex-col items-center justify-center gap-3 bg-stone-50">
          <div className="flex h-12 w-12 animate-pulse items-center justify-center rounded-2xl bg-emerald-700 text-lg font-bold text-white">
            S
          </div>
          <p className="text-sm text-stone-400">Loading...</p>
        </div>
      </AuthGuard>
    );
  if (!receipt)
    return (
      <AuthGuard>
        <p className="p-6 text-rose-500">Receipt not found</p>
      </AuthGuard>
    );

  return (
    <AuthGuard>
      <div className="mx-auto max-w-2xl px-4 py-6 space-y-6 animate-page">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-stone-900">
            {receipt.merchant_name || "Processing..."}
          </h1>
          {receipt.receipt_date && (
            <p className="text-sm text-stone-500">{receipt.receipt_date}</p>
          )}
          <div className="mt-2 flex gap-3 text-sm text-stone-600">
            {receipt.subtotal && <span>Subtotal: <span className="font-mono">${receipt.subtotal}</span></span>}
            {receipt.tax && <span>Tax: <span className="font-mono">${receipt.tax}</span></span>}
            {receipt.service_charge && <span>Service: <span className="font-mono">${receipt.service_charge}</span></span>}
            {receipt.total && <span className="font-semibold">Total: <span className="font-mono">${receipt.total}</span></span>}
          </div>
        </div>

        {/* Processing state */}
        {receipt.status === "processing" && (
          <div className="rounded-xl bg-amber-50 p-4 text-center">
            <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-amber-600 border-t-transparent" />
            <p className="mt-2 text-sm text-amber-700">AI is extracting receipt details...</p>
          </div>
        )}

        {/* Line Items + Assignments */}
        {receipt.line_items.length > 0 && (
          <section>
            <h2 className="mb-3 text-lg font-semibold text-stone-900">Line Items</h2>
            <div className="space-y-3">
              {receipt.line_items.map((li) => (
                <div key={li.id} className="rounded-xl border-l-4 border-l-emerald-600 bg-white p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-stone-900">{li.description}</span>
                    <span className="font-semibold font-mono text-stone-900">${li.amount}</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {members.map((m) => (
                      <button
                        key={m.user_id}
                        onClick={() => toggleAssignment(li.id, m.user_id)}
                        disabled={saving}
                        className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                          isAssigned(li.id, m.user_id)
                            ? "bg-emerald-700 text-white"
                            : "bg-stone-100 text-stone-600 hover:bg-stone-200"
                        }`}
                      >
                        {m.display_name || "Unknown"}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Payment */}
        <section>
          <h2 className="mb-3 text-lg font-semibold text-stone-900">Record Payment</h2>
          <div className="rounded-xl border-l-4 border-l-emerald-600 bg-white p-4 space-y-3 shadow-sm">
            <div>
              <label className="block text-sm font-medium text-stone-700">Who paid?</label>
              <select
                value={payUserId}
                onChange={(e) => setPayUserId(e.target.value)}
                className="mt-1 block w-full rounded-xl border border-stone-300 px-3 py-2 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
              >
                <option value="">Select member</option>
                {members.map((m) => (
                  <option key={m.user_id} value={m.user_id}>
                    {m.display_name || "Unknown"}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-700">Amount</label>
              <input
                type="number"
                step="0.01"
                value={payAmount}
                onChange={(e) => setPayAmount(e.target.value)}
                placeholder={receipt.total || "0.00"}
                className="mt-1 block w-full rounded-xl border border-stone-300 px-3 py-2 font-mono focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
              />
            </div>
            <button
              onClick={handlePayment}
              disabled={!payUserId || !payAmount}
              className="w-full rounded-xl bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50"
            >
              Record Payment
            </button>
          </div>
        </section>

        {/* Receipt image */}
        {receipt.image_url && (
          <section>
            <h2 className="mb-3 text-lg font-semibold text-stone-900">Receipt Image</h2>
            <img src={receipt.image_url} alt="Receipt" className="w-full rounded-xl border border-stone-200" />
          </section>
        )}
      </div>
    </AuthGuard>
  );
}
