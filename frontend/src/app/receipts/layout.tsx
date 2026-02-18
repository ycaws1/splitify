"use client";

import { AuthGuard } from "@/components/auth-provider";
import { AppHeader } from "@/components/app-header";
import { BottomNav } from "@/components/bottom-nav";

export default function ReceiptsLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="min-h-screen bg-stone-50 pb-20">
        <AppHeader showBack />
        <main className="animate-page">{children}</main>
        <BottomNav />
      </div>
    </AuthGuard>
  );
}
