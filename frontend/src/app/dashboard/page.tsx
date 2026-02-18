"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { Group } from "@/types";

export default function DashboardPage() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    apiFetch("/api/groups")
      .then((data) => { if (!cancelled) setGroups(data); })
      .catch((err) => { if (!cancelled) console.error(err); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-stone-900">My Groups</h1>
        <Link
          href="/groups/new"
          className="rounded-xl bg-emerald-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-800"
        >
          + New Group
        </Link>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-stone-200" />
          ))}
        </div>
      ) : groups.length === 0 ? (
        <div className="rounded-2xl border-2 border-dashed border-stone-300 p-16 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-stone-100 text-xl">
            +
          </div>
          <p className="font-medium text-stone-700">No groups yet</p>
          <p className="mt-1 text-sm text-stone-500">Create one to start splitting bills</p>
        </div>
      ) : (
        <div className="space-y-3">
          {groups.map((group) => (
            <Link
              key={group.id}
              href={`/groups/${group.id}`}
              className="block rounded-xl border-l-4 border-l-emerald-600 bg-white p-4 shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5"
            >
              <h2 className="font-semibold text-stone-900">{group.name}</h2>
              <p className="mt-1 text-sm text-stone-500">
                Created {new Date(group.created_at).toLocaleDateString()}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
