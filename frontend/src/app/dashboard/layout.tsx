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
      <div className="min-h-screen bg-stone-50">
        <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/80 backdrop-blur-md px-4 py-3">
          <div className="mx-auto flex max-w-2xl items-center justify-between">
            <Link href="/dashboard" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-700 text-sm font-bold text-white">
                S
              </div>
              <span className="text-lg font-bold text-stone-900">Splitify</span>
            </Link>
            <button
              onClick={handleLogout}
              className="rounded-lg px-3 py-1.5 text-sm text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-700"
            >
              Logout
            </button>
          </div>
        </header>
        <main className="mx-auto max-w-2xl px-4 py-6 animate-page">{children}</main>
      </div>
    </AuthGuard>
  );
}
