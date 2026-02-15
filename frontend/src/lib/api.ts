import { createClient } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Cache session to avoid repeated getSession() calls
let cachedToken: string | null = null;
let tokenExpiry = 0;

async function getAccessToken(): Promise<string | null> {
  const now = Date.now();
  if (cachedToken && now < tokenExpiry) return cachedToken;

  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    cachedToken = session.access_token;
    // Cache until 30s before expiry
    tokenExpiry = (session.expires_at ?? 0) * 1000 - 30_000;
    return cachedToken;
  }
  cachedToken = null;
  return null;
}

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = await getAccessToken();

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || res.statusText);
  }

  if (res.status === 204) return null;
  return res.json();
}
