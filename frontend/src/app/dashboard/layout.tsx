"use client";

import { AuthGuard } from "@/components/auth-provider";
import { AppHeader } from "@/components/app-header";
import { BottomNav } from "@/components/bottom-nav";
import { PushRegistration } from "@/components/push-registration";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <PushRegistration />
      <div className="min-h-screen bg-stone-50 pb-20">
        <AppHeader showProfile />
        <main className="mx-auto max-w-2xl px-4 py-6 animate-page">{children}</main>
        <BottomNav />
      </div>
    </AuthGuard>
  );
}
