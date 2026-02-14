"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type { User } from "@supabase/supabase-js";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const supabase = createClient();

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (!session) {
          router.push("/");
        } else {
          setUser(session.user);
        }
        setLoading(false);
      }
    );
    return () => subscription.unsubscribe();
  }, [router, supabase.auth]);

  if (loading) return (
    <div className="flex h-screen flex-col items-center justify-center gap-3 bg-stone-50">
      <div className="flex h-12 w-12 animate-pulse items-center justify-center rounded-2xl bg-emerald-700 text-lg font-bold text-white">
        S
      </div>
      <p className="text-sm text-stone-400">Loading...</p>
    </div>
  );
  if (!user) return null;

  return <>{children}</>;
}
