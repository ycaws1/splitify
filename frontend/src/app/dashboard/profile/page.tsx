"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

export default function ProfilePage() {
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    apiFetch("/api/auth/me")
      .then((data) => {
        setDisplayName(data.display_name);
        setEmail(data.email);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      await apiFetch("/api/auth/me", {
        method: "PATCH",
        body: JSON.stringify({ display_name: displayName }),
      });
      setMessage("Saved!");
      setTimeout(() => setMessage(""), 2000);
    } catch (err) {
      setMessage("Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="h-40 animate-pulse rounded-xl bg-stone-200" />;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-stone-900">Profile</h1>
      <form onSubmit={handleSave} className="space-y-4 rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Email</label>
          <p className="rounded-xl bg-stone-50 px-4 py-2.5 text-stone-500">{email}</p>
        </div>
        <div>
          <label htmlFor="displayName" className="block text-sm font-medium text-stone-700 mb-1">
            Display Name
          </label>
          <input
            id="displayName"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="w-full rounded-xl border border-stone-300 px-4 py-2.5 text-stone-900 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
          />
        </div>
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={saving}
            className="rounded-xl bg-emerald-700 px-6 py-2.5 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
          {message && (
            <span className={`text-sm ${message === "Saved!" ? "text-emerald-600" : "text-rose-500"}`}>
              {message}
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
