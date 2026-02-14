"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { AuthGuard } from "@/components/auth-guard";

export default function NewGroupPage() {
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    try {
      const group = await apiFetch("/api/groups", {
        method: "POST",
        body: JSON.stringify({ name: name.trim() }),
      });
      router.push(`/groups/${group.id}`);
    } catch (err) {
      console.error(err);
      setSubmitting(false);
    }
  };

  return (
    <AuthGuard>
      <div className="mx-auto max-w-2xl px-4 py-8 animate-page">
        <h1 className="mb-6 text-2xl font-bold text-stone-900">Create Group</h1>
        <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-stone-700">
                Group Name
              </label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Trip to Tokyo"
                className="mt-1 block w-full rounded-xl border border-stone-300 px-4 py-2.5 text-stone-900 shadow-sm focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
                required
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-emerald-800 disabled:opacity-50"
            >
              {submitting ? "Creating..." : "Create Group"}
            </button>
          </form>
        </div>
      </div>
    </AuthGuard>
  );
}
