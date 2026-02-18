"use client";

import { useState, useRef, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { invalidateCache } from "@/hooks/use-cached-fetch";
import { COMMON_CURRENCIES, getCurrencySymbol } from "@/lib/currency";
import type { Group } from "@/types";

type Tab = "upload" | "manual";

interface ManualItem {
  description: string;
  quantity: string;
  amount: string;
}

export default function NewReceiptPage() {
  const params = useParams();
  const groupId = params.id as string;
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [tab, setTab] = useState<Tab>("upload");

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [uploadCurrency, setUploadCurrency] = useState("SGD");

  // Manual state
  const [merchantName, setMerchantName] = useState("");
  const [currency, setCurrency] = useState("SGD");
  const [receiptDate, setReceiptDate] = useState("");
  const [tax, setTax] = useState("9");
  const [taxIsPercent, setTaxIsPercent] = useState(true);
  const [serviceCharge, setServiceCharge] = useState("6");
  const [scIsPercent, setScIsPercent] = useState(true);
  const [items, setItems] = useState<ManualItem[]>([
    { description: "", quantity: "1", amount: "" },
  ]);
  const [exchangeRate, setExchangeRate] = useState("1");
  const [fetchingRate, setFetchingRate] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [group, setGroup] = useState<Group | null>(null);

  const [error, setError] = useState<string | null>(null);

  const baseCurrency = group?.base_currency || "SGD";
  const showExchangeRate = currency !== baseCurrency;

  // Fetch group info
  useEffect(() => {
    apiFetch(`/api/groups/${groupId}`).then(setGroup).catch(() => { });
  }, [groupId]);

  // Fetch exchange rate when currency changes
  useEffect(() => {
    if (!group) return;
    if (currency === baseCurrency) {
      setExchangeRate("1");
      return;
    }
    setFetchingRate(true);
    apiFetch(`/api/exchange-rate?from_currency=${currency}&to_currency=${baseCurrency}`)
      .then((data) => setExchangeRate(String(data.rate)))
      .catch(() => setExchangeRate("1"))
      .finally(() => setFetchingRate(false));
  }, [currency, baseCurrency, group]);

  // Upload handler
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setPreview(URL.createObjectURL(file));
    setUploading(true);
    setError(null);

    try {
      const supabase = createClient();
      const fileName = `${groupId}/${Date.now()}-${file.name}`;
      const { data, error: uploadError } = await supabase.storage
        .from("receipts")
        .upload(fileName, file);

      if (uploadError) throw new Error(uploadError.message);

      const { data: urlData } = supabase.storage
        .from("receipts")
        .getPublicUrl(data.path);

      const receipt = await apiFetch(`/api/groups/${groupId}/receipts`, {
        method: "POST",
        body: JSON.stringify({ image_url: urlData.publicUrl, currency: uploadCurrency || undefined }),
      });

      // Force refresh of receipts list
      invalidateCache(`/api/groups/${groupId}/receipts`);
      router.push(`/groups/${groupId}/receipts`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setUploading(false);
    }
  };

  // Manual item helpers
  const addItem = () => setItems([...items, { description: "", quantity: "1", amount: "" }]);
  const removeItem = (index: number) => {
    if (items.length === 1) return;
    setItems(items.filter((_, i) => i !== index));
  };
  const updateItem = (index: number, field: keyof ManualItem, value: string) => {
    const updated = [...items];
    updated[index] = { ...updated[index], [field]: value };
    setItems(updated);
  };

  const subtotal = items.reduce((sum, item) => sum + (parseFloat(item.amount) || 0), 0);
  const taxAmount = taxIsPercent ? subtotal * (parseFloat(tax) || 0) / 100 : (parseFloat(tax) || 0);
  const scAmount = scIsPercent ? subtotal * (parseFloat(serviceCharge) || 0) / 100 : (parseFloat(serviceCharge) || 0);
  const total = subtotal + taxAmount + scAmount;

  // Manual submit
  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!merchantName.trim() || items.some((i) => !i.description.trim() || !i.amount)) return;

    setSubmitting(true);
    setError(null);
    try {
      const receipt = await apiFetch(`/api/groups/${groupId}/receipts/manual`, {
        method: "POST",
        body: JSON.stringify({
          merchant_name: merchantName.trim(),
          currency,
          exchange_rate: parseFloat(exchangeRate) || 1,
          receipt_date: receiptDate || null,
          tax: tax ? parseFloat(taxAmount.toFixed(2)) : null,
          service_charge: serviceCharge ? parseFloat(scAmount.toFixed(2)) : null,
          items: items.map((i) => ({
            description: i.description.trim(),
            quantity: parseFloat(i.quantity) || 1,
            amount: parseFloat(i.amount),
          })),
        }),
      });

      // Force refresh of receipts list
      invalidateCache(`/api/groups/${groupId}/receipts`);
      router.push(`/receipts/${receipt.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create receipt");
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 space-y-6">
      <h1 className="text-2xl font-bold text-stone-900">Add Receipt</h1>

      {/* Tab selector */}
      <div className="flex rounded-xl bg-stone-100 p-1">
        <button
          onClick={() => setTab("upload")}
          className={`flex-1 rounded-lg py-2 text-sm font-medium transition-colors ${tab === "upload" ? "bg-white text-stone-900 shadow-sm" : "text-stone-500"
            }`}
        >
          Upload Photo
        </button>
        <button
          onClick={() => setTab("manual")}
          className={`flex-1 rounded-lg py-2 text-sm font-medium transition-colors ${tab === "manual" ? "bg-white text-stone-900 shadow-sm" : "text-stone-500"
            }`}
        >
          Enter Manually
        </button>
      </div>

      {error && (
        <div className="rounded-xl bg-rose-50 p-3 text-sm text-rose-600">{error}</div>
      )}

      {/* Upload tab */}
      {tab === "upload" && (
        <>
          <div className="mb-6">
            <label className="mb-2 block text-sm font-medium text-stone-700">
              Receipt Currency
            </label>
            <select
              value={uploadCurrency}
              onChange={(e) => setUploadCurrency(e.target.value)}
              disabled={uploading || !!preview}
              className="w-full rounded-xl border-stone-200 bg-white p-3 text-sm shadow-sm focus:border-emerald-500 focus:ring-emerald-500 disabled:opacity-50"
            >
              {COMMON_CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c} ({getCurrencySymbol(c)})
                </option>
              ))}
            </select>
          </div>
          {preview ? (
            <div className="space-y-4">
              <img src={preview} alt="Receipt preview" className="w-full rounded-xl border border-stone-200" />
              {uploading && (
                <div className="text-center">
                  <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
                  <p className="mt-2 text-sm text-stone-500">Creating receipt...</p>
                </div>
              )}
            </div>
          ) : (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="cursor-pointer rounded-2xl border-2 border-dashed border-stone-300 p-12 text-center hover:border-emerald-400 transition-colors"
            >
              <div className="text-4xl text-stone-400 mb-2">&#128247;</div>
              <p className="text-stone-500">Tap to take a photo or select an image</p>
              <p className="mt-1 text-sm text-stone-400">AI will extract items automatically</p>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
          />
        </>
      )}

      {/* Manual tab */}
      {tab === "manual" && (
        <form onSubmit={handleManualSubmit} className="space-y-4">
          {/* Merchant & date */}
          <div className="rounded-2xl border border-stone-200 bg-white p-4 space-y-3 shadow-sm">
            <div>
              <label className="block text-sm font-medium text-stone-700">Merchant Name</label>
              <input
                type="text"
                value={merchantName}
                onChange={(e) => setMerchantName(e.target.value)}
                placeholder="e.g., Restaurant ABC"
                className="mt-1 block w-full rounded-xl border border-stone-300 px-3 py-2 text-stone-900 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-stone-700">Currency</label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="mt-1 block w-full rounded-xl border border-stone-300 px-3 py-2 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
                >
                  {COMMON_CURRENCIES.map((c) => (
                    <option key={c} value={c}>{c} ({getCurrencySymbol(c)})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-stone-700">Date</label>
                <input
                  type="date"
                  value={receiptDate}
                  onChange={(e) => setReceiptDate(e.target.value)}
                  className="mt-1 block w-full rounded-xl border border-stone-300 px-3 py-2 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
                />
              </div>
            </div>
            {showExchangeRate && (
              <div>
                <label className="block text-sm font-medium text-stone-700">
                  Exchange Rate
                  <span className="text-xs text-stone-400 ml-1">
                    (1 {currency} = ? {baseCurrency})
                  </span>
                </label>
                <div className="relative mt-1">
                  <input
                    type="number"
                    value={exchangeRate}
                    onChange={(e) => setExchangeRate(e.target.value)}
                    step="0.000001"
                    min="0"
                    className="block w-full rounded-xl border border-stone-300 px-3 py-2 font-mono text-sm focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
                  />
                  {fetchingRate && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2">
                      <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-stone-400">
                  {getCurrencySymbol(currency)} {total.toFixed(2)} = {getCurrencySymbol(baseCurrency)} {(total * parseFloat(exchangeRate || "0")).toFixed(2)}
                </p>
              </div>
            )}
          </div>

          {/* Line items */}
          <div className="rounded-2xl border border-stone-200 bg-white p-4 space-y-3 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-stone-900">Items</h2>
              <button
                type="button"
                onClick={addItem}
                className="rounded-lg bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
              >
                + Add Item
              </button>
            </div>
            {items.map((item, i) => (
              <div key={i} className="flex gap-2 items-start">
                <div className="flex-1">
                  <input
                    type="text"
                    value={item.description}
                    onChange={(e) => updateItem(i, "description", e.target.value)}
                    placeholder="Item name"
                    className="block w-full rounded-xl border border-stone-300 px-3 py-2 text-sm focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
                    required
                  />
                </div>
                <div className="w-16">
                  <input
                    type="number"
                    value={item.quantity}
                    onChange={(e) => updateItem(i, "quantity", e.target.value)}
                    placeholder="Qty"
                    min="1"
                    step="1"
                    className="block w-full rounded-xl border border-stone-300 px-2 py-2 text-sm text-center font-mono focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
                  />
                </div>
                <div className="w-24">
                  <input
                    type="number"
                    value={item.amount}
                    onChange={(e) => updateItem(i, "amount", e.target.value)}
                    placeholder="0.00"
                    step="0.01"
                    className="block w-full rounded-xl border border-stone-300 px-2 py-2 text-sm text-right font-mono focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
                    required
                  />
                </div>
                {items.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeItem(i)}
                    className="mt-1 text-stone-400 hover:text-rose-500 text-lg leading-none"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Tax, service charge, total */}
          <div className="rounded-2xl border border-stone-200 bg-white p-4 space-y-3 shadow-sm">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="flex items-center justify-between">
                  <label className="block text-sm font-medium text-stone-700">Tax</label>
                  <button
                    type="button"
                    onClick={() => { setTaxIsPercent(!taxIsPercent); setTax(""); }}
                    className="rounded-md bg-stone-100 px-2 py-0.5 text-xs font-medium text-stone-600 hover:bg-stone-200"
                  >
                    {taxIsPercent ? "%" : currency}
                  </button>
                </div>
                <div className="relative mt-1">
                  <input
                    type="number"
                    value={tax}
                    onChange={(e) => setTax(e.target.value)}
                    placeholder={taxIsPercent ? "e.g. 6" : "0.00"}
                    step={taxIsPercent ? "0.1" : "0.01"}
                    className="block w-full rounded-xl border border-stone-300 px-3 py-2 pr-10 font-mono text-sm focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-stone-400">
                    {taxIsPercent ? "%" : currency}
                  </span>
                </div>
                {taxIsPercent && tax && (
                  <p className="mt-1 text-xs text-stone-400 font-mono">= {currency} {taxAmount.toFixed(2)}</p>
                )}
              </div>
              <div>
                <div className="flex items-center justify-between">
                  <label className="block text-sm font-medium text-stone-700">Service Charge</label>
                  <button
                    type="button"
                    onClick={() => { setScIsPercent(!scIsPercent); setServiceCharge(""); }}
                    className="rounded-md bg-stone-100 px-2 py-0.5 text-xs font-medium text-stone-600 hover:bg-stone-200"
                  >
                    {scIsPercent ? "%" : currency}
                  </button>
                </div>
                <div className="relative mt-1">
                  <input
                    type="number"
                    value={serviceCharge}
                    onChange={(e) => setServiceCharge(e.target.value)}
                    placeholder={scIsPercent ? "e.g. 10" : "0.00"}
                    step={scIsPercent ? "0.1" : "0.01"}
                    className="block w-full rounded-xl border border-stone-300 px-3 py-2 pr-10 font-mono text-sm focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-stone-400">
                    {scIsPercent ? "%" : currency}
                  </span>
                </div>
                {scIsPercent && serviceCharge && (
                  <p className="mt-1 text-xs text-stone-400 font-mono">= {currency} {scAmount.toFixed(2)}</p>
                )}
              </div>
            </div>
            <div className="flex items-center justify-between border-t border-stone-100 pt-3">
              <span className="text-sm font-medium text-stone-700">Total</span>
              <span className="text-lg font-bold font-mono text-stone-900">
                {currency} {total.toFixed(2)}
              </span>
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-emerald-700 px-4 py-3 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50"
          >
            {submitting ? "Creating..." : "Create Receipt"}
          </button>
        </form>
      )}
    </div>
  );
}
