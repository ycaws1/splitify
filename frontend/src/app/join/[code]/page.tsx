"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { AuthGuard } from "@/components/auth-guard";

export default function JoinGroupPage() {
  const params = useParams();
  const code = params.code as string;
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch(`/api/groups/join/${code}`, { method: "POST" })
      .then((group) => router.push(`/groups/${group.id}`))
      .catch((err) => setError(err.message));
  }, [code, router]);

  return (
    <AuthGuard>
      <div className="flex min-h-screen items-center justify-center animate-page">
        {error ? (
          <div className="text-center">
            <p className="text-rose-500">{error}</p>
            <a href="/dashboard" className="mt-4 inline-block text-emerald-700 hover:text-emerald-900">
              Go to Dashboard
            </a>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="flex h-12 w-12 animate-pulse items-center justify-center rounded-2xl bg-emerald-700 text-lg font-bold text-white">
              S
            </div>
            <p className="text-stone-500">Joining group...</p>
          </div>
        )}
      </div>
    </AuthGuard>
  );
}
