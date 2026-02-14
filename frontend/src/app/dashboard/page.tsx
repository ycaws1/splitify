"use client";

import { AuthGuard } from "@/components/auth-guard";

export default function DashboardPage() {
  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50 p-6">
        <h1 className="text-2xl font-bold text-gray-900">My Groups</h1>
        <p className="mt-2 text-gray-500">Your groups will appear here.</p>
      </div>
    </AuthGuard>
  );
}
