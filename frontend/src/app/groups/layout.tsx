"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { AuthGuard } from "@/components/auth-provider";

export default function GroupsLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  const handleLogout = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
  };

  return (
    <AuthGuard>
      <div className="min-h-screen bg-stone-50">
        <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/80 backdrop-blur-md px-4 py-3">
          <div className="mx-auto flex max-w-2xl items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => router.back()}
                className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-700"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
                Back
              </button>
              <Link href="/dashboard" className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-700 text-sm font-bold text-white">
                  S
                </div>
              </Link>
            </div>
            <button
              onClick={handleLogout}
              className="rounded-lg px-3 py-1.5 text-sm text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-700"
            >
              Logout
            </button>
          </div>
        </header>
        <main className="animate-page">{children}</main>
      </div>
    </AuthGuard>
  );
}
