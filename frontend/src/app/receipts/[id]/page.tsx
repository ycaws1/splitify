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
        <p className="p-6 text-gray-500">Loading...</p>
      </AuthGuard>
    );
  if (!receipt)
    return (
      <AuthGuard>
        <p className="p-6 text-red-500">Receipt not found</p>
      </AuthGuard>
    );

  return (
    <AuthGuard>
      <div className="mx-auto max-w-2xl px-4 py-6 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {receipt.merchant_name || "Processing..."}
          </h1>
          {receipt.receipt_date && (
            <p className="text-sm text-gray-500">{receipt.receipt_date}</p>
          )}
          <div className="mt-2 flex gap-3 text-sm text-gray-600">
            {receipt.subtotal && <span>Subtotal: ${receipt.subtotal}</span>}
            {receipt.tax && <span>Tax: ${receipt.tax}</span>}
            {receipt.service_charge && <span>Service: ${receipt.service_charge}</span>}
            {receipt.total && <span className="font-semibold">Total: ${receipt.total}</span>}
          </div>
        </div>

        {/* Processing state */}
        {receipt.status === "processing" && (
          <div className="rounded-lg bg-yellow-50 p-4 text-center">
            <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-yellow-600 border-t-transparent" />
            <p className="mt-2 text-sm text-yellow-700">AI is extracting receipt details...</p>
          </div>
        )}

        {/* Line Items + Assignments */}
        {receipt.line_items.length > 0 && (
          <section>
            <h2 className="mb-3 text-lg font-semibold text-gray-900">Line Items</h2>
            <div className="space-y-3">
              {receipt.line_items.map((li) => (
                <div key={li.id} className="rounded-lg border bg-white p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-gray-900">{li.description}</span>
                    <span className="font-semibold text-gray-900">${li.amount}</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {members.map((m) => (
                      <button
                        key={m.user_id}
                        onClick={() => toggleAssignment(li.id, m.user_id)}
                        disabled={saving}
                        className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                          isAssigned(li.id, m.user_id)
                            ? "bg-indigo-600 text-white"
                            : "bg-gray-100 text-gray-600 hover:bg-gray-200"
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
          <h2 className="mb-3 text-lg font-semibold text-gray-900">Record Payment</h2>
          <div className="rounded-lg border bg-white p-4 space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700">Who paid?</label>
              <select
                value={payUserId}
                onChange={(e) => setPayUserId(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2"
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
              <label className="block text-sm font-medium text-gray-700">Amount</label>
              <input
                type="number"
                step="0.01"
                value={payAmount}
                onChange={(e) => setPayAmount(e.target.value)}
                placeholder={receipt.total || "0.00"}
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2"
              />
            </div>
            <button
              onClick={handlePayment}
              disabled={!payUserId || !payAmount}
              className="w-full rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              Record Payment
            </button>
          </div>
        </section>

        {/* Receipt image */}
        {receipt.image_url && (
          <section>
            <h2 className="mb-3 text-lg font-semibold text-gray-900">Receipt Image</h2>
            <img src={receipt.image_url} alt="Receipt" className="w-full rounded-lg border" />
          </section>
        )}
      </div>
    </AuthGuard>
  );
}
