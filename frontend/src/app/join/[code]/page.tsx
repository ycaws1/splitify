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
      <div className="flex min-h-screen items-center justify-center">
        {error ? (
          <div className="text-center">
            <p className="text-red-500">{error}</p>
            <a href="/dashboard" className="mt-4 text-indigo-600 hover:text-indigo-800">
              Go to Dashboard
            </a>
          </div>
        ) : (
          <p className="text-gray-500">Joining group...</p>
        )}
      </div>
    </AuthGuard>
  );
}
