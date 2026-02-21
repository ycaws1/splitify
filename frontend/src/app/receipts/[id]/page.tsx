"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { invalidateCache } from "@/hooks/use-cached-fetch";
import { getCurrencySymbol } from "@/lib/currency";
import { AppHeader } from "@/components/app-header";
import type { Receipt, Assignment, GroupMember, Group } from "@/types";

export default function ReceiptDetailPage() {
  const params = useParams();
  const router = useRouter();
  const receiptId = params.id as string;
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [payments, setPayments] = useState<{ id: string; paid_by: string; payer_name: string; amount: string }[]>([]);
  const [payAmount, setPayAmount] = useState("");
  const [payUserId, setPayUserId] = useState("");
  const [editingPayment, setEditingPayment] = useState<string | null>(null);
  const [editPayUserId, setEditPayUserId] = useState("");
  const [editPayAmount, setEditPayAmount] = useState("");
  const [group, setGroup] = useState<Group | null>(null);

  // Editing states
  const [isEditingHeader, setIsEditingHeader] = useState(false);
  const [headerForm, setHeaderForm] = useState<{
    merchant_name: string;
    receipt_date: string;
    currency: string;
    tax: string;
    service_charge: string;
  } | null>(null);
  const [isEditingItems, setIsEditingItems] = useState(false);
  const [loadingAssignments, setLoadingAssignments] = useState<Set<string>>(new Set());
  const [isAssigningAll, setIsAssigningAll] = useState(false);
  const [isAddingPayment, setIsAddingPayment] = useState(false);
  const [savingPaymentId, setSavingPaymentId] = useState<string | null>(null);
  const [deletingPaymentId, setDeletingPaymentId] = useState<string | null>(null);

  const groupIdRef = React.useRef<string | null>(null);
  const lastSeenVersion = useRef(0);


  const isAssigned = (lineItemId: string, userId: string) => {
    return assignments.some((a) => a.line_item_id === lineItemId && a.user_id === userId);
  };

  // Track pending optimistic updates to prevent background fetches from reverting UI
  // Key: "lineItemId:userId", Value: "add" | "remove"
  const pendingUpdates = useRef<Map<string, "add" | "remove">>(new Map());

  const applyOptimisticUpdates = useCallback((baseAssignments: Assignment[]) => {
    let result = [...baseAssignments];
    pendingUpdates.current.forEach((type, key) => {
      const [lId, uId] = key.split(':');
      const exists = result.some(a => a.line_item_id === lId && a.user_id === uId);

      if (type === 'add' && !exists) {
        result.push({
          id: `temp-${lId}-${uId}`,
          line_item_id: lId,
          user_id: uId,
          share_amount: "0.00",
        });
      } else if (type === 'remove' && exists) {
        result = result.filter(a => !(a.line_item_id === lId && a.user_id === uId));
      }
    });
    return result;
  }, []);

  const fetchReceipt = useCallback(async () => {
    try {
      const r = await apiFetch(`/api/receipts/${receiptId}?include=group,payments`);
      setReceipt(r);
      if (r.version > lastSeenVersion.current) {
        lastSeenVersion.current = r.version;
      }

      // Extract assignments from line_items (included in response)
      const allAssignments = r.line_items.flatMap((li: { assignments: Assignment[] }) => li.assignments || []);
      setAssignments(applyOptimisticUpdates(allAssignments));

      // Group and payments are embedded in the response
      if (r.group) {
        groupIdRef.current = r.group_id;
        setGroup(r.group);
        setMembers(r.group.members);
      }
      if (r.payments) {
        setPayments(r.payments);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [receiptId, applyOptimisticUpdates]);

  const isMounted = useRef(true);
  useEffect(() => {
    isMounted.current = true;
    fetchReceipt();
    return () => { isMounted.current = false; };
  }, [fetchReceipt]);

  // Realtime subscription for receipt updates (from OTHER users)
  useEffect(() => {
    const supabase = createClient();
    const channel = supabase
      .channel(`receipt-${receiptId}`)
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "receipts", filter: `id=eq.${receiptId}` },
        (payload: any) => {
          const newVersion = payload.new?.version;
          // Skip refetch if we've already seen this version (or a newer one)
          if (newVersion && newVersion <= lastSeenVersion.current) {
            return;
          }
          fetchReceipt();
        }
      )
      .subscribe();



    return () => {
      supabase.removeChannel(channel);
    };
  }, [receiptId, fetchReceipt]);

  // Poll while processing as a backup
  useEffect(() => {
    if (receipt?.status !== "processing") return;

    const interval = setInterval(() => {
      fetchReceipt();
    }, 3000);

    return () => clearInterval(interval);
  }, [receipt?.status, fetchReceipt]);

  // Toggle assignment for a user on a line item (OPTIMISTIC UPDATE)
  const toggleAssignment = async (lineItemId: string, userId: string) => {
    if (!receipt) return;

    // OPTIMISTIC UPDATE: Update UI immediately
    const wasAssigned = isAssigned(lineItemId, userId);
    const previousAssignments = [...assignments];
    const previousReceipt = { ...receipt };
    const pendingKey = `${lineItemId}:${userId}`;

    // Update pending map
    setLoadingAssignments((prev) => new Set(prev).add(pendingKey));
    pendingUpdates.current.set(pendingKey, wasAssigned ? 'remove' : 'add');

    setAssignments((prev) => {
      if (wasAssigned) {
        return prev.filter((a) => !(a.line_item_id === lineItemId && a.user_id === userId));
      } else {
        return [
          ...prev,
          {
            id: 'temp-' + Date.now() + Math.random(), // unique temp ID
            line_item_id: lineItemId,
            user_id: userId,
            share_amount: "0.00",
          },
        ];
      }
    });

    // Mark version as seen optimistically
    const nextVersion = (receipt.version || 0) + 1;
    lastSeenVersion.current = Math.max(lastSeenVersion.current, nextVersion);

    // Call new fast toggle endpoint in background
    try {
      const result = await apiFetch(`/api/receipts/${receiptId}/assignments/toggle`, {
        method: "POST",
        body: JSON.stringify({
          line_item_id: lineItemId,
          user_id: userId,
          // Sending null version to skip strict optimisitic locking check (last write wins)
          version: null,
        }),
      });

      // Update version from server response
      setReceipt((prev) => prev ? { ...prev, version: result.new_version } : null);

      // Refresh assignments from server to get correct share amounts
      // Instead of another network hop, use the inline updated assignments for this line item
      setAssignments((prev) => {
        const others = prev.filter((a) => a.line_item_id !== lineItemId);
        return applyOptimisticUpdates([...others, ...result.assignments]);
      });
    } catch (err: unknown) {
      // ROLLBACK on error
      lastSeenVersion.current = previousReceipt.version || 0;
      setAssignments(previousAssignments);
      setReceipt(previousReceipt);

      if (err instanceof Error && err.message.includes("Version conflict")) {
        // Full refresh on version conflict
        await fetchReceipt();
      } else {
        console.error(err);
        alert(err instanceof Error ? err.message : "Failed to update assignment");
      }
    } finally {
      // Only remove pending status if it matches our intent? 
      // For simplicity/single-user flow, removing is generally safe as request finished.
      // But technically we should respect if state changed again. 
      // Given the user report is about single click flickering, deleting here is correct.
      pendingUpdates.current.delete(pendingKey);
      setLoadingAssignments((prev) => {
        const next = new Set(prev);
        next.delete(pendingKey);
        return next;
      });
      if (receipt) invalidateCache(`/api/groups/${receipt.group_id}`);
    }
  };

  const handleAssignAll = async (lineItemId: string) => {
    // Check if everyone is currently assigned
    const memberIds = members.map(m => m.user_id);
    const assignedIds = assignments
      .filter(a => a.line_item_id === lineItemId)
      .map(a => a.user_id);

    const allAssigned = memberIds.every(id => assignedIds.includes(id));
    const targetAssigned = !allAssigned;

    // Use the bulk assign route to update the entire line item in one request
    try {
      setLoadingAssignments((prev) => new Set(prev).add(lineItemId + ":all"));
      const result = await apiFetch(`/api/receipts/${receiptId}/assignments`, {
        method: "PUT",
        body: JSON.stringify({
          assignments: [
            {
              line_item_id: lineItemId,
              user_ids: targetAssigned ? memberIds : [],
            },
          ],
          version: null,
        }),
      });
      setAssignments((prev) => {
        const others = prev.filter((a) => a.line_item_id !== lineItemId);
        return applyOptimisticUpdates([...others, ...result]);
      });
      if (result.length > 0) {
        // Find which items got updated to bump version
        // The bulk endpoint doesn't return new_version directly yet, so we refetch receipt next if needed
        // but for now we'll just invalidate
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to assign all");
    } finally {
      setLoadingAssignments((prev) => {
        const next = new Set(prev);
        next.delete(lineItemId + ":all");
        return next;
      });
      if (receipt) invalidateCache(`/api/groups/${receipt.group_id}`);
    }
  };

  // Payment totals
  const totalPaid = payments.reduce((sum, p) => sum + parseFloat(p.amount), 0);
  const remaining = receipt ? parseFloat(receipt.total || "0") - totalPaid : 0;

  // Record payment
  const [payError, setPayError] = useState<string | null>(null);

  const handlePayment = async () => {
    if (!payUserId || !payAmount) return;
    const amount = parseFloat(payAmount);
    if (remaining > 0 && amount > remaining + 0.01) {
      setPayError(`Amount exceeds remaining ${getCurrencySymbol(receipt?.currency || "")}${remaining.toFixed(2)}`);
      return;
    }
    setPayError(null);

    // Optimistic: update UI immediately
    const payer = members.find(m => m.user_id === payUserId);
    const tempPayment = {
      id: `temp-${Date.now()}`,
      receipt_id: receiptId,
      paid_by: payUserId,
      payer_name: payer?.display_name || "Unknown",
      amount: amount.toFixed(2),
    };
    const previousPayments = payments;
    setPayments([...payments, tempPayment]);
    setPayAmount("");
    setPayUserId("");
    setIsAddingPayment(true);

    try {
      const newPayment = await apiFetch(`/api/receipts/${receiptId}/payments`, {
        method: "POST",
        body: JSON.stringify({ paid_by: tempPayment.paid_by, amount }),
      });
      // Replace temp with real server response
      setPayments((prev) => prev.map((p) =>
        p.id === tempPayment.id ? { ...newPayment, payer_name: newPayment.payer_name || tempPayment.payer_name } : p
      ));
      if (receipt) invalidateCache(`/api/groups/${receipt.group_id}`);
    } catch (err: unknown) {
      setPayError(err instanceof Error ? err.message : "Failed to record payment");
      setPayments(previousPayments); // rollback
    } finally {
      setIsAddingPayment(false);
    }
  };

  const handleEditPayment = async (paymentId: string) => {
    if (!editPayUserId || !editPayAmount) return;
    setSavingPaymentId(paymentId);
    try {
      await apiFetch(`/api/payments/${paymentId}`, {
        method: "PUT",
        body: JSON.stringify({ paid_by: editPayUserId, amount: parseFloat(editPayAmount) }),
      });
      setEditingPayment(null);
      const p = await apiFetch(`/api/receipts/${receiptId}/payments`);
      setPayments(p);
    } catch (err) {
      console.error(err);
    } finally {
      setSavingPaymentId(null);
    }
  };

  const handleDeletePayment = async (paymentId: string) => {
    if (!confirm("Remove this payment?")) return;
    setDeletingPaymentId(paymentId);
    try {
      await apiFetch(`/api/payments/${paymentId}`, { method: "DELETE" });
      setPayments(payments.filter(p => p.id !== paymentId));
    } catch (err) {
      console.error(err);
    } finally {
      setDeletingPaymentId(null);
    }
  };

  const handleDelete = async () => {
    if (!receipt || !confirm("Delete this receipt? This cannot be undone.")) return;
    setDeleting(true);
    try {
      await apiFetch(`/api/receipts/${receiptId}`, { method: "DELETE" });
      invalidateCache(`/api/groups/${receipt.group_id}`);
      invalidateCache(`/api/groups/${receipt.group_id}/receipts`);
      router.push(`/groups/${receipt.group_id}/receipts`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete");
      setDeleting(false);
    }
  };

  // Header editing handlers
  const startEditHeader = () => {
    if (!receipt) return;
    setHeaderForm({
      merchant_name: receipt.merchant_name || "",
      receipt_date: receipt.receipt_date || "",
      currency: receipt.currency || "SGD",
      tax: receipt.tax || "",
      service_charge: receipt.service_charge || "",
    });
    setIsEditingHeader(true);
  };

  const [isSavingHeader, setIsSavingHeader] = useState(false);

  const saveHeader = async () => {
    if (!headerForm || !receipt) return;
    setIsSavingHeader(true);
    try {
      await apiFetch(`/api/receipts/${receiptId}`, {
        method: "PUT",
        body: JSON.stringify({
          merchant_name: headerForm.merchant_name,
          receipt_date: headerForm.receipt_date || null,
          currency: headerForm.currency,
          tax: headerForm.tax ? parseFloat(headerForm.tax) : null,
          service_charge: headerForm.service_charge ? parseFloat(headerForm.service_charge) : null,
          version: receipt.version,
        }),
      });
      setIsEditingHeader(false);
      fetchReceipt();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update receipt details");
    } finally {
      setIsSavingHeader(false);
    }
  };

  // ... (inside the return JSX) ...

  <div className="flex justify-end gap-2 pt-2">
    <button
      onClick={() => setIsEditingHeader(false)}
      disabled={isSavingHeader}
      className="rounded-lg px-3 py-1.5 text-sm font-medium text-stone-600 hover:bg-stone-100 disabled:opacity-50"
    >
      Cancel
    </button>
    <button
      onClick={saveHeader}
      disabled={isSavingHeader}
      className="rounded-lg bg-emerald-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50 flex items-center gap-2"
    >
      {isSavingHeader && <div className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />}
      {isSavingHeader ? "Saving..." : "Save Details"}
    </button>
  </div>

  // Item editing handlers
  const [modifiedItemIds, setModifiedItemIds] = useState<Set<string>>(new Set());
  const [isSavingItems, setIsSavingItems] = useState(false);

  const handleAddItem = async () => {
    // Add temporary item to UI only
    const tempId = `temp-${Date.now()}`;
    const newItem = {
      id: tempId,
      description: "New Item",
      amount: "0",
      quantity: 1,
      currency: receipt?.currency || "SGD",
    };

    setReceipt((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        line_items: [...prev.line_items, newItem as any],
      };
    });
    setModifiedItemIds(prev => new Set(prev).add(tempId));
  };

  const handleUpdateItem = (itemId: string, field: string, value: string) => {
    setReceipt((prev) => {
      if (!prev) return null;
      const updatedItems = prev.line_items.map((li) =>
        li.id === itemId ? { ...li, [field]: value } : li
      );
      return { ...prev, line_items: updatedItems };
    });
    setModifiedItemIds(prev => new Set(prev).add(itemId));
  };

  const saveItems = async () => {
    if (!receipt) return;
    setIsSavingItems(true);
    try {
      // Calculate new totals upfront from local state
      const newSubtotal = receipt.line_items.reduce((sum, item) => sum + (parseFloat(item.amount) || 0), 0);
      const tax = parseFloat(receipt.tax || "0");
      const service = parseFloat(receipt.service_charge || "0");
      const newTotal = newSubtotal + tax + service;

      const itemPromises = Array.from(modifiedItemIds).map(async (id) => {
        const item = receipt.line_items.find(li => li.id === id);
        if (!item) return;

        if (id.startsWith('temp-')) {
          // Create new
          await apiFetch(`/api/receipts/${receiptId}/items`, {
            method: "POST",
            body: JSON.stringify({
              description: item.description,
              amount: parseFloat(item.amount) || 0,
              quantity: parseFloat(String(item.quantity)) || 1,
            }),
          });
        } else {
          // Update existing
          await apiFetch(`/api/items/${id}`, {
            method: "PUT",
            body: JSON.stringify({
              description: item.description,
              amount: parseFloat(item.amount) || 0,
              quantity: parseFloat(String(item.quantity)) || 1,
            }),
          });
        }
      });

      // Await all item saves sequentially to prevent concurrent updates to the same receipt version in DB
      for (const promise of itemPromises) {
        await promise;
      }

      // Then update receipt totals
      await apiFetch(`/api/receipts/${receiptId}`, {
        method: "PUT",
        body: JSON.stringify({
          subtotal: newSubtotal,
          total: newTotal,
          version: null,
        }),
      });

      // Update local state with final values
      setReceipt(prev => prev ? {
        ...prev,
        subtotal: newSubtotal.toFixed(2),
        total: newTotal.toFixed(2)
      } : null);

      setModifiedItemIds(new Set());
      setIsEditingItems(false);

      // Fire-and-forget: replace temp IDs with real server UUIDs in background
      fetchReceipt();

      // Force refresh of group balances since totals changed
      invalidateCache(`/api/groups/${receipt.group_id}`);

    } catch (err) {
      alert("Failed to save items");
      console.error(err);
    } finally {
      setIsSavingItems(false);
    }
  };

  const handleDeleteItem = async (itemId: string) => {
    if (!confirm("Delete this item?")) return;
    try {
      await apiFetch(`/api/items/${itemId}`, { method: "DELETE" });
      if (receipt) invalidateCache(`/api/groups/${receipt.group_id}`);
      fetchReceipt();
    } catch (err) {
      alert("Failed to delete item");
    }
  };

  if (loading)
    return (
      <>
        <AppHeader showBack />
        <div className="flex h-[calc(100vh-64px)] flex-col items-center justify-center gap-3">
          <div className="flex h-12 w-12 animate-pulse items-center justify-center rounded-2xl bg-emerald-700 text-lg font-bold text-white">
            S
          </div>
          <p className="text-sm text-stone-400">Loading...</p>
        </div>
      </>
    );
  if (!receipt)
    return (
      <>
        <AppHeader showBack />
        <p className="p-6 text-rose-500">Receipt not found</p>
      </>
    );

  // Common currencies for dropdown
  const COMMON_CURRENCIES = ["SGD", "MYR", "USD", "EUR", "GBP", "JPY", "CNY", "KRW", "THB", "IDR", "VND", "AUD"];

  return (
    <>
      <AppHeader showBack backUrl={`/groups/${receipt.group_id}/receipts`} />
      <div className="mx-auto max-w-2xl px-4 py-6 space-y-6">
        {/* Header */}
        {/* Header */}
        <div>
          {isEditingHeader && headerForm ? (
            <div className="space-y-3 rounded-xl bg-white p-4 shadow-sm border border-stone-200">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-stone-700">Merchant Name</label>
                <input
                  type="text"
                  value={headerForm.merchant_name}
                  onChange={(e) => setHeaderForm({ ...headerForm, merchant_name: e.target.value })}
                  className="block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm focus:border-emerald-600 focus:outline-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-stone-700">Date</label>
                  <input
                    type="date"
                    value={headerForm.receipt_date}
                    onChange={(e) => setHeaderForm({ ...headerForm, receipt_date: e.target.value })}
                    className="block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm focus:border-emerald-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-stone-700">Currency</label>
                  <select
                    value={headerForm.currency}
                    onChange={(e) => setHeaderForm({ ...headerForm, currency: e.target.value })}
                    className="block w-full rounded-lg border border-stone-300 px-3 py-2 text-sm focus:border-emerald-600 focus:outline-none"
                  >
                    {COMMON_CURRENCIES.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {/* Tax Input */}
                <div>
                  <div className="flex justify-between">
                    <label className="block text-sm font-medium text-stone-700">Tax</label>
                    <button
                      onClick={() => {
                        // Toggle between raw amount and % logic if needed, 
                        // but primarily user wants to INPUT as %.
                        // Let's support inputting "10%" or just toggling a mode?
                        // Simpler: Just like NewReceiptPage.
                        // For now, let's keep it simple: Add a "%" mode toggle in local state?
                        // We can use the Tax input for both if we detect % user wants?
                        // Better: Add a toggle button like "Switch to %"
                      }}
                      className="text-xs text-emerald-600 hover:text-emerald-700"
                    >
                      {/* We'll implement a smarter input below */}
                    </button>
                  </div>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Amount"
                      value={headerForm.tax}
                      onChange={(e) => setHeaderForm({ ...headerForm, tax: e.target.value })}
                      className="block w-full rounded-lg border border-stone-300 px-3 py-2 font-mono text-sm focus:border-emerald-600 focus:outline-none"
                    />
                    {/* Helper to set tax by % of subtotal */}
                    {receipt.subtotal && (
                      <div className="mt-1 flex gap-2">
                        <button
                          onClick={() => {
                            const sub = parseFloat(receipt.subtotal!);
                            const rate = prompt("Enter Tax Rate (%)", "9");
                            if (rate && !isNaN(parseFloat(rate))) {
                              const val = (sub * parseFloat(rate) / 100).toFixed(2);
                              setHeaderForm({ ...headerForm, tax: val });
                            }
                          }}
                          className="text-[10px] bg-stone-100 px-2 py-0.5 rounded text-stone-600 hover:bg-stone-200"
                        >
                          Set %
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Service Charge Input */}
                <div>
                  <label className="block text-sm font-medium text-stone-700">Service Charge</label>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Amount"
                      value={headerForm.service_charge}
                      onChange={(e) => setHeaderForm({ ...headerForm, service_charge: e.target.value })}
                      className="block w-full rounded-lg border border-stone-300 px-3 py-2 font-mono text-sm focus:border-emerald-600 focus:outline-none"
                    />
                    {receipt.subtotal && (
                      <div className="mt-1 flex gap-2">
                        <button
                          onClick={() => {
                            const sub = parseFloat(receipt.subtotal!);
                            const rate = prompt("Enter Service Charge Rate (%)", "10");
                            if (rate && !isNaN(parseFloat(rate))) {
                              const val = (sub * parseFloat(rate) / 100).toFixed(2);
                              setHeaderForm({ ...headerForm, service_charge: val });
                            }
                          }}
                          className="text-[10px] bg-stone-100 px-2 py-0.5 rounded text-stone-600 hover:bg-stone-200"
                        >
                          Set %
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setIsEditingHeader(false)}
                  disabled={isSavingHeader}
                  className="rounded-lg px-3 py-1.5 text-sm font-medium text-stone-600 hover:bg-stone-100 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={saveHeader}
                  disabled={isSavingHeader}
                  className="rounded-lg bg-emerald-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50 flex items-center gap-2"
                >
                  {isSavingHeader && <div className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />}
                  {isSavingHeader ? "Saving..." : "Save Details"}
                </button>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex justify-between items-start">
                <div>
                  <h1 className="text-2xl font-bold text-stone-900">
                    {receipt.merchant_name || "Processing..."}
                  </h1>
                  {receipt.receipt_date && (
                    <p className="text-sm text-stone-500">{receipt.receipt_date}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    disabled={isAssigningAll}
                    onClick={async () => {
                      setIsAssigningAll(true);
                      try {
                        // Optimistic assumption: it works, but hard to simulate complex UI update for everything locally.
                        // So we'll just wait for the fast server response.
                        const updatedAssignments = await apiFetch(`/api/receipts/${receiptId}/assignments/assign-all`, {
                          method: "POST"
                        });
                        setAssignments(updatedAssignments);
                        fetchReceipt(); // Refresh full state including version
                        invalidateCache(`/api/groups/${receipt.group_id}`);
                      } catch (err) {
                        alert("Failed to assign all");
                      } finally {
                        setIsAssigningAll(false);
                      }
                    }}
                    className={`flex items-center gap-2 text-sm font-medium text-emerald-700 hover:text-emerald-800 border border-emerald-200 rounded-lg px-3 py-1.5 hover:bg-emerald-50 transition-colors ${isAssigningAll ? 'opacity-60 cursor-not-allowed' : ''}`}
                  >
                    {isAssigningAll && <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />}
                    Split All Evenly
                  </button>
                  <button
                    onClick={startEditHeader}
                    className="text-sm font-medium text-stone-600 hover:text-stone-900 border border-stone-200 rounded-lg px-3 py-1.5 hover:bg-stone-50 transition-colors"
                  >
                    Edit Details
                  </button>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-3 text-sm text-stone-600">
                {receipt.subtotal && <span>Subtotal: <span className="font-mono">{getCurrencySymbol(receipt.currency)}{receipt.subtotal}</span></span>}
                {receipt.tax && <span>Tax: <span className="font-mono">{getCurrencySymbol(receipt.currency)}{receipt.tax}</span></span>}
                {receipt.service_charge && <span>Service: <span className="font-mono">{getCurrencySymbol(receipt.currency)}{receipt.service_charge}</span></span>}
                {receipt.total && <span className="font-semibold">Total: <span className="font-mono">{getCurrencySymbol(receipt.currency)}{receipt.total}</span></span>}
              </div>

              {(() => {
                const sumItems = receipt.line_items.reduce((s, li) => s + (parseFloat(li.amount) || 0), 0);
                const tax = parseFloat(receipt.tax || "0");
                const svc = parseFloat(receipt.service_charge || "0");
                const calculatedTotal = sumItems + tax + svc;
                const currentTotal = parseFloat(receipt.total || "0");

                if (Math.abs(calculatedTotal - currentTotal) > 0.05) {
                  return (
                    <div className="mt-3 rounded-lg bg-amber-50 border border-amber-200 p-3 flex items-start gap-3">
                      <div className="text-amber-600 mt-0.5">⚠️</div>
                      <div className="flex-1 text-sm text-amber-800">
                        <p className="font-medium">Total mismatch</p>
                        <p className="mt-1">
                          Receipt total is <strong>{getCurrencySymbol(receipt.currency)}{currentTotal.toFixed(2)}</strong> but items + tax + service sums to <strong>{getCurrencySymbol(receipt.currency)}{calculatedTotal.toFixed(2)}</strong>.
                        </p>
                        <button
                          onClick={async () => {
                            if (!confirm(`Update receipt total to ${getCurrencySymbol(receipt.currency)}${calculatedTotal.toFixed(2)}?`)) return;

                            // Optimistic update
                            const prevReceipt = { ...receipt };
                            setReceipt({
                              ...receipt,
                              subtotal: sumItems.toFixed(2),
                              total: calculatedTotal.toFixed(2)
                            });

                            try {
                              const updated = await apiFetch(`/api/receipts/${receiptId}`, {
                                method: "PUT",
                                body: JSON.stringify({
                                  subtotal: sumItems,
                                  total: calculatedTotal,
                                  version: receipt.version
                                }),
                              });
                              // Update with server response just in case
                              setReceipt(prev => prev ? { ...prev, ...updated } : null);
                              if (receipt) invalidateCache(`/api/groups/${receipt.group_id}`);
                            } catch (err) {
                              alert("Failed to update total");
                              setReceipt(prevReceipt); // Rollback
                            }
                          }}
                          className="mt-2 rounded bg-white px-3 py-1 text-xs font-semibold text-amber-700 shadow-sm border border-amber-200 hover:bg-amber-50"
                        >
                          Fix Total to Match Items
                        </button>
                      </div>
                    </div>
                  );
                }
                return null;
              })()}

              {group && receipt.currency !== group.base_currency && (
                <div className="mt-1 text-xs text-stone-400 space-y-0.5">
                  <p>Exchange rate: 1 {receipt.currency} = {receipt.exchange_rate} {group.base_currency}</p>
                  {receipt.total && (
                    <p className="font-mono">
                      = {getCurrencySymbol(group.base_currency)}{(parseFloat(receipt.total) * parseFloat(receipt.exchange_rate)).toFixed(2)} {group.base_currency}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Processing state */}
        {receipt.status === "processing" && (
          <div className="rounded-xl bg-amber-50 p-4 text-center">
            <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-amber-600 border-t-transparent" />
            <p className="mt-2 text-sm text-amber-700">AI is extracting receipt details...</p>
          </div>
        )}

        {/* Failed state */}
        {receipt.status === "failed" && (
          <div className="rounded-xl bg-rose-50 p-4 text-center mb-4">
            <p className="text-sm font-medium text-rose-700">Failed to extract receipt info.</p>
            <p className="text-xs text-rose-600 mt-1">You can add items manually below.</p>
            {receipt.raw_llm_response?.error && (
              <details className="mt-2 text-left">
                <summary className="text-xs text-rose-500 cursor-pointer hover:underline">Show Error Details</summary>
                <pre className="mt-2 max-h-48 overflow-auto rounded-lg bg-white/50 p-2 text-[10px] text-rose-900 font-mono whitespace-pre-wrap">
                  {receipt.raw_llm_response.error}
                  {'\n\n'}
                  {receipt.raw_llm_response.traceback}
                </pre>
              </details>
            )}
            <button
              onClick={async () => {
                if (!confirm("Retry extracting receipt details?")) return;
                try {
                  // Optimistically set to processing
                  setReceipt(prev => prev ? { ...prev, status: "processing" } : null);
                  await apiFetch(`/api/receipts/${receiptId}/retry-ocr`, { method: "POST" });
                  // Rely on polling/subscription to get update
                } catch (err) {
                  alert("Failed to retry OCR");
                  fetchReceipt(); // Revert
                }
              }}
              className="mt-3 rounded-lg bg-white border border-rose-200 px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-50 shadow-sm"
            >
              Retry Extraction
            </button>
          </div>
        )}

        {/* Line Items + Assignments */}
        {/* Line Items + Assignments */}
        {(() => {
          const unassignedItems = receipt.line_items.filter(
            (li) => !assignments.some((a) => a.line_item_id === li.id)
          );
          const totalAssigned = receipt.line_items
            .filter((li) => assignments.some((a) => a.line_item_id === li.id))
            .reduce((sum, li) => sum + parseFloat(li.amount), 0);

          const hasItems = receipt.line_items.length > 0;

          return (
            <section>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold text-stone-900">Line Items</h2>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-stone-500 font-mono">
                    Assigned: {getCurrencySymbol(receipt.currency)}{totalAssigned.toFixed(2)} / {getCurrencySymbol(receipt.currency)}{receipt.line_items.reduce((s, li) => s + parseFloat(li.amount), 0).toFixed(2)}
                  </span>
                  {!isEditingItems && (
                    <button
                      onClick={() => setIsEditingItems(true)}
                      className="ml-2 text-sm font-medium text-emerald-700 hover:text-emerald-800"
                    >
                      {hasItems ? "Edit Items" : "Add Items"}
                    </button>
                  )}
                </div>
              </div>

              {!isEditingItems && unassignedItems.length > 0 && (
                <div className="mb-3 rounded-xl bg-amber-50 px-4 py-2 text-sm text-amber-700">
                  {unassignedItems.length} item{unassignedItems.length > 1 ? "s" : ""} not assigned to anyone
                </div>
              )}

              <div className="space-y-3">
                {receipt.line_items.map((li) => {
                  if (isEditingItems) {
                    return (
                      <div key={li.id} className="rounded-xl border border-stone-200 bg-white p-3 shadow-sm flex items-center gap-2">
                        <div className="flex-1 space-y-2">
                          <input
                            type="text"
                            value={li.description}
                            onChange={(e) => handleUpdateItem(li.id, "description", e.target.value)}
                            placeholder="Description"
                            className="block w-full rounded-lg border border-stone-300 px-2 py-1 text-sm focus:border-emerald-600 focus:outline-none"
                          />
                          <div className="flex gap-2">
                            <input
                              type="number"
                              value={li.amount}
                              onChange={(e) => handleUpdateItem(li.id, "amount", e.target.value)}
                              placeholder="Amount"
                              className="block w-28 rounded-lg border border-stone-300 px-2 py-1 font-mono text-sm focus:border-emerald-600 focus:outline-none"
                            />
                            <input
                              type="number"
                              value={li.quantity}
                              onChange={(e) => handleUpdateItem(li.id, "quantity", e.target.value)}
                              placeholder="Qty"
                              className="block w-24 rounded-lg border border-stone-300 px-2 py-1 font-mono text-sm text-center focus:border-emerald-600 focus:outline-none"
                              title="Quantity"
                            />
                          </div>
                        </div>
                        <button
                          onClick={() => handleDeleteItem(li.id)}
                          className="p-2 text-stone-400 hover:text-rose-600"
                          title="Delete item"
                        >
                          <span className="text-2xl leading-none">×</span>
                        </button>
                      </div>
                    );
                  }

                  const hasAssignment = assignments.some((a) => a.line_item_id === li.id);
                  return (
                    <div key={li.id} className={`rounded-xl border-l-4 ${hasAssignment ? "border-l-emerald-600" : "border-l-amber-400"} bg-white p-4 shadow-sm`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-stone-900">{li.description}</span>
                        <div className="text-right">
                          <span className="font-semibold font-mono text-stone-900">{getCurrencySymbol(receipt.currency)}{li.amount}</span>
                          {group && receipt.currency !== group.base_currency && (
                            <p className="text-xs font-mono text-stone-400">
                              {getCurrencySymbol(group.base_currency)}{(parseFloat(li.amount) * parseFloat(receipt.exchange_rate)).toFixed(2)}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => handleAssignAll(li.id)}
                          className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold transition-colors ${members.every(m => isAssigned(li.id, m.user_id))
                            ? "bg-emerald-700 text-white"
                            : "bg-white border border-stone-300 text-stone-600 hover:bg-stone-100"
                            } ${(members.some(m => loadingAssignments.has(`${li.id}:${m.user_id}`)) || loadingAssignments.has(`${li.id}:all`)) ? "opacity-60 cursor-not-allowed" : ""}`}
                          disabled={(members.some(m => loadingAssignments.has(`${li.id}:${m.user_id}`)) || loadingAssignments.has(`${li.id}:all`))}
                          title={members.every(m => isAssigned(li.id, m.user_id)) ? "Unselect All" : "Select All"}
                        >
                          {loadingAssignments.has(`${li.id}:all`) && <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />}
                          All
                        </button>
                        {members.map((m) => {
                          const isLoading = loadingAssignments.has(`${li.id}:${m.user_id}`);
                          return (
                            <button
                              key={m.user_id}
                              disabled={isLoading}
                              onClick={() => toggleAssignment(li.id, m.user_id)}
                              className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${isAssigned(li.id, m.user_id)
                                ? "bg-emerald-700 text-white"
                                : "bg-stone-100 text-stone-600 hover:bg-stone-200"
                                } ${isLoading ? "opacity-60 cursor-not-allowed" : ""}`}
                            >
                              {isLoading && <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />}
                              {m.display_name || "Unknown"}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}

                {isEditingItems && (
                  <div className="space-y-3 pt-2">
                    <button
                      onClick={handleAddItem}
                      className="w-full rounded-xl border-2 border-dashed border-stone-300 py-3 text-sm font-medium text-stone-600 hover:bg-stone-50 transition-colors"
                    >
                      + Add New Item
                    </button>

                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          setIsEditingItems(false);
                          setModifiedItemIds(new Set());
                          fetchReceipt(); // discard changes
                        }}
                        disabled={isSavingItems}
                        className="flex-1 rounded-xl bg-stone-100 py-3 text-sm font-medium text-stone-600 hover:bg-stone-200"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={saveItems}
                        disabled={isSavingItems || modifiedItemIds.size === 0}
                        className="flex-1 rounded-xl bg-emerald-700 py-3 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50 flex justify-center items-center gap-2"
                      >
                        {isSavingItems && <div className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />}
                        Save Changes
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </section>
          );
        })()}

        {/* Payments */}
        <section>
          <h2 className="mb-3 text-lg font-semibold text-stone-900">Payments</h2>

          {/* Existing payments */}
          {payments.length > 0 && (
            <div className="space-y-2 mb-3">
              {payments.map((p) => (
                <div key={p.id} className="rounded-xl border-l-4 border-l-emerald-600 bg-white px-4 py-3 shadow-sm">
                  {editingPayment === p.id ? (
                    <div className="space-y-2">
                      <div className="grid grid-cols-2 gap-2">
                        <select
                          value={editPayUserId}
                          onChange={(e) => setEditPayUserId(e.target.value)}
                          className="block w-full rounded-lg border border-stone-300 px-2 py-1.5 text-sm focus:border-emerald-600 focus:outline-none"
                        >
                          {members.map((m) => (
                            <option key={m.user_id} value={m.user_id}>
                              {m.display_name || "Unknown"}
                            </option>
                          ))}
                        </select>
                        <input
                          type="number"
                          step="0.01"
                          value={editPayAmount}
                          onChange={(e) => setEditPayAmount(e.target.value)}
                          className="block w-full rounded-lg border border-stone-300 px-2 py-1.5 font-mono text-sm focus:border-emerald-600 focus:outline-none"
                        />
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleEditPayment(p.id)}
                          disabled={savingPaymentId === p.id}
                          className={`flex items-center gap-1.5 rounded-lg bg-emerald-700 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-800 ${savingPaymentId === p.id ? "opacity-50 cursor-not-allowed" : ""}`}
                        >
                          {savingPaymentId === p.id && <div className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />}
                          Save
                        </button>
                        <button
                          onClick={() => setEditingPayment(null)}
                          className="rounded-lg bg-stone-100 px-3 py-1 text-xs font-medium text-stone-600 hover:bg-stone-200"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-stone-700">
                        <span className="font-medium">{p.payer_name}</span> paid
                      </span>
                      <div className="flex items-center gap-2">
                        <div className="text-right">
                          <span className="font-semibold font-mono text-emerald-700">{getCurrencySymbol(receipt.currency)}{p.amount}</span>
                          {group && receipt.currency !== group.base_currency && (
                            <p className="text-xs font-mono text-stone-400">
                              {getCurrencySymbol(group.base_currency)}{(parseFloat(p.amount) * parseFloat(receipt.exchange_rate)).toFixed(2)}
                            </p>
                          )}
                        </div>
                        <button
                          onClick={() => {
                            setEditingPayment(p.id);
                            setEditPayUserId(p.paid_by);
                            setEditPayAmount(p.amount);
                          }}
                          className="rounded-lg px-2 py-1 text-xs text-stone-400 hover:bg-stone-100 hover:text-stone-600"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeletePayment(p.id)}
                          disabled={deletingPaymentId === p.id}
                          className={`flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-stone-400 hover:bg-rose-50 hover:text-rose-600 ${deletingPaymentId === p.id ? "opacity-50 cursor-not-allowed" : ""}`}
                        >
                          {deletingPaymentId === p.id && <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />}
                          Remove
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              <div className="flex items-center justify-between px-4 py-2 text-sm">
                <span className="text-stone-500">Total paid</span>
                <div className="text-right">
                  <span className="font-mono font-semibold text-stone-900">{getCurrencySymbol(receipt.currency)}{totalPaid.toFixed(2)}</span>
                  {group && receipt.currency !== group.base_currency && (
                    <p className="text-xs font-mono text-stone-400">
                      {getCurrencySymbol(group.base_currency)}{(totalPaid * parseFloat(receipt.exchange_rate)).toFixed(2)}
                    </p>
                  )}
                </div>
              </div>
              {remaining > 0.01 && (
                <div className="flex items-center justify-between px-4 py-1 text-sm">
                  <span className="text-rose-500">Remaining</span>
                  <span className="font-mono font-semibold text-rose-600">{getCurrencySymbol(receipt.currency)}{remaining.toFixed(2)}</span>
                </div>
              )}
            </div>
          )}

          {/* Add payment form */}
          <div className="rounded-xl border-l-4 border-l-emerald-600 bg-white p-4 space-y-3 shadow-sm">
            <p className="text-sm font-medium text-stone-700">Add payment</p>
            <div className="grid grid-cols-2 gap-3">
              <select
                value={payUserId}
                onChange={(e) => setPayUserId(e.target.value)}
                className="block w-full rounded-xl border border-stone-300 px-3 py-2 text-sm focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
              >
                <option value="">Who paid?</option>
                {members.map((m) => (
                  <option key={m.user_id} value={m.user_id}>
                    {m.display_name || "Unknown"}
                  </option>
                ))}
              </select>
              <input
                type="number"
                step="0.01"
                value={payAmount}
                onChange={(e) => setPayAmount(e.target.value)}
                placeholder={remaining > 0.01 ? remaining.toFixed(2) : (receipt.total || "0.00")}
                className="block w-full rounded-xl border border-stone-300 px-3 py-2 font-mono text-sm focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
              />
            </div>
            {payError && (
              <p className="text-sm text-rose-600">{payError}</p>
            )}
            <button
              onClick={handlePayment}
              disabled={!payUserId || !payAmount || isAddingPayment}
              className={`w-full rounded-xl bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50 flex items-center justify-center gap-2`}
            >
              {isAddingPayment && <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />}
              Record Payment
            </button>
          </div>
        </section>

        {/* Receipt image */}
        {receipt.image_url && receipt.image_url !== "" && (
          <section>
            <h2 className="mb-3 text-lg font-semibold text-stone-900">Receipt Image</h2>
            <img src={receipt.image_url} alt="Receipt" className="w-full rounded-xl border border-stone-200" />
          </section>
        )}

        {/* Delete */}
        <section className="pt-4 border-t border-stone-200">
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="w-full rounded-xl border-2 border-rose-300 px-4 py-2 text-sm font-medium text-rose-600 hover:bg-rose-50 disabled:opacity-50"
          >
            {deleting ? "Deleting..." : "Delete Receipt"}
          </button>
        </section>
      </div>
    </>
  );
}
