"use client";

import { AuthGuard } from "@/components/auth-provider";
import { BottomNav } from "@/components/bottom-nav";

export default function ReceiptsLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="min-h-screen bg-stone-50 pb-20">
        <main className="animate-page">{children}</main>
        <BottomNav />
      </div>
    </AuthGuard>
  );
}
