"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { AuthGuard } from "@/components/auth-guard";
import { PushRegistration } from "@/components/push-registration";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const supabase = createClient();

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push("/");
  };

  return (
    <AuthGuard>
      <PushRegistration />
      <div className="min-h-screen bg-gray-50">
        <header className="sticky top-0 z-10 border-b bg-white px-4 py-3">
          <div className="mx-auto flex max-w-2xl items-center justify-between">
            <Link href="/dashboard" className="text-xl font-bold text-gray-900">
              Splitify
            </Link>
            <button
              onClick={handleLogout}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Logout
            </button>
          </div>
        </header>
        <main className="mx-auto max-w-2xl px-4 py-6">{children}</main>
      </div>
    </AuthGuard>
  );
}
