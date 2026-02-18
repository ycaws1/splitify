"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "@/lib/api";

const CACHE_PREFIX = "splitify_cache_";
const DEFAULT_TTL = 5 * 60 * 1000; // 5 minutes

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

function getCached<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(CACHE_PREFIX + key);
    if (!raw) return null;
    const entry: CacheEntry<T> = JSON.parse(raw);
    // Return cached data regardless of age — staleness is handled by the caller
    return entry.data;
  } catch {
    return null;
  }
}

function setCache<T>(key: string, data: T) {
  try {
    const entry: CacheEntry<T> = { data, timestamp: Date.now() };
    sessionStorage.setItem(CACHE_PREFIX + key, JSON.stringify(entry));
  } catch {
    // sessionStorage full or unavailable — ignore
  }
}

export function invalidateCache(keyPattern: string) {
  try {
    const toRemove: string[] = [];
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i);
      if (key?.startsWith(CACHE_PREFIX) && key.includes(keyPattern)) {
        toRemove.push(key);
      }
    }
    toRemove.forEach((k) => sessionStorage.removeItem(k));
  } catch {
    // ignore
  }
}

/**
 * SWR-style hook: returns cached data instantly, then revalidates in the background.
 * - Shows cached data immediately (no loading spinner on revisit)
 * - Fetches fresh data and updates when ready
 * - `loading` is only true on first load with no cache
 */
export function useCachedFetch<T>(
  path: string | null,
  options?: { transform?: (data: any) => T }
) {
  const cached = path ? getCached<T>(path) : null;
  const [data, setData] = useState<T | null>(cached);
  const [loading, setLoading] = useState(!cached);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const refetch = useCallback(async (showLoading = false) => {
    if (!path) return;
    if (showLoading) setLoading(true);
    try {
      const raw = await apiFetch(path);
      const result = options?.transform ? options.transform(raw) : raw;
      if (mountedRef.current) {
        setData(result as T);
        setError(null);
        setCache(path, result);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : "Fetch failed");
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [path]);

  // Initial fetch — always revalidate, but only show loading if no cache
  useEffect(() => {
    if (!path) return;
    refetch();
  }, [path, refetch]);

  return { data, loading, error, refetch, setData };
}
