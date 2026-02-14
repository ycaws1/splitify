"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { Group } from "@/types";

export default function DashboardPage() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/api/groups")
      .then(setGroups)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">My Groups</h1>
        <Link
          href="/groups/new"
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          New Group
        </Link>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading groups...</p>
      ) : groups.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-200 p-12 text-center">
          <p className="text-gray-500">No groups yet. Create one to get started!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {groups.map((group) => (
            <Link
              key={group.id}
              href={`/groups/${group.id}`}
              className="block rounded-lg border bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
            >
              <h2 className="font-semibold text-gray-900">{group.name}</h2>
              <p className="mt-1 text-sm text-gray-500">
                Created {new Date(group.created_at).toLocaleDateString()}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
