"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function BottomNav() {
  const pathname = usePathname();

  const isHome = pathname.startsWith("/dashboard");

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-20 border-t border-stone-200 bg-white/95 backdrop-blur-md pb-[env(safe-area-inset-bottom)]">
      <div className="mx-auto flex max-w-2xl items-center justify-around px-4 py-2">
        <Link
          href="/dashboard"
          className={`flex flex-col items-center gap-0.5 rounded-lg px-6 py-1.5 text-xs font-medium transition-colors ${
            isHome ? "text-emerald-700" : "text-stone-400 hover:text-stone-600"
          }`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={isHome ? 2.5 : 2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8" />
            <path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
          </svg>
          Home
        </Link>
      </div>
    </nav>
  );
}
