"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";

export default function LoginPage() {
  const supabase = createClient();
  const router = useRouter();

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        if (session) {
          // Sync user to backend
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/callback`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              id: session.user.id,
              email: session.user.email,
              display_name: session.user.user_metadata.full_name || session.user.email?.split("@")[0] || "User",
              avatar_url: session.user.user_metadata.avatar_url || null,
            }),
          });
          router.push("/dashboard");
        }
      }
    );
    return () => subscription.unsubscribe();
  }, [router, supabase.auth]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg">
        <h1 className="mb-2 text-center text-3xl font-bold text-gray-900">Splitify</h1>
        <p className="mb-6 text-center text-sm text-gray-500">Split bills with friends, effortlessly</p>
        <Auth
          supabaseClient={supabase}
          appearance={{ theme: ThemeSupa }}
          providers={[]}
          redirectTo={typeof window !== "undefined" ? `${window.location.origin}/dashboard` : ""}
        />
      </div>
    </div>
  );
}
