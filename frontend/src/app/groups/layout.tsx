"use client";

import { usePathname } from "next/navigation";
import { AuthGuard } from "@/components/auth-provider";
import { AppHeader } from "@/components/app-header";
import { BottomNav } from "@/components/bottom-nav";

export default function GroupsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // Extract groupId from /groups/[id]/...
  const match = pathname.match(/^\/groups\/([^\/]+)/);
  const groupId = match ? match[1] : null;

  // Determine custom back URL
  let backUrl = undefined;
  if (groupId && groupId !== "new") {
    // If we're deeper than /groups/[id] (e.g. /groups/[id]/receipts), go back to group overview
    if (pathname.split("/").length > 3) {
      backUrl = `/groups/${groupId}`;
    } else {
      // At /groups/[id], go back to dashboard
      backUrl = "/dashboard";
    }
  } else if (pathname === "/groups/new") {
    backUrl = "/dashboard";
  }

  return (
    <AuthGuard>
      <div className="min-h-screen bg-stone-50 pb-20">
        <AppHeader showBack backUrl={backUrl} />
        <main className="animate-page">{children}</main>
        <BottomNav />
      </div>
    </AuthGuard>
  );
}
