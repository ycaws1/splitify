"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useAuth } from "@/components/auth-provider";
import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";

export default function LoginPage() {
  const supabase = createClient();
  const router = useRouter();
  const { session } = useAuth();
  const syncedRef = useRef(false);

  // If already logged in, redirect immediately
  useEffect(() => {
    if (session && !syncedRef.current) {
      syncedRef.current = true;
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/callback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: session.user.id,
          email: session.user.email,
          display_name: session.user.user_metadata.full_name || session.user.email?.split("@")[0] || "User",
          avatar_url: session.user.user_metadata.avatar_url || null,
        }),
      }).then(() => router.push("/dashboard"));
    }
  }, [session, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-50 px-4">
      <div className="animate-page w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-700 text-2xl text-white shadow-lg">
            S
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-stone-900">Splitify</h1>
          <p className="mt-1 text-stone-500">Split bills with friends, effortlessly</p>
        </div>
        <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <Auth
            supabaseClient={supabase}
            appearance={{
              theme: ThemeSupa,
              variables: {
                default: {
                  colors: {
                    brand: '#047857',
                    brandAccent: '#065f46',
                    inputBorder: '#d6d3d1',
                    inputBorderFocus: '#047857',
                    inputBorderHover: '#a8a29e',
                  },
                  borderWidths: { buttonBorderWidth: '0px', inputBorderWidth: '1px' },
                  radii: { borderRadiusButton: '12px', inputBorderRadius: '12px' },
                },
              },
            }}
            providers={[]}
            redirectTo={typeof window !== "undefined" ? `${window.location.origin}/dashboard` : ""}
          />
        </div>
      </div>
    </div>
  );
}
