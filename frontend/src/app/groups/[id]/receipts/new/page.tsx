"use client";

import { useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { AuthGuard } from "@/components/auth-guard";

export default function UploadReceiptPage() {
  const params = useParams();
  const groupId = params.id as string;
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setPreview(URL.createObjectURL(file));
    setUploading(true);
    setError(null);

    try {
      const supabase = createClient();
      const fileName = `${groupId}/${Date.now()}-${file.name}`;
      const { data, error: uploadError } = await supabase.storage
        .from("receipts")
        .upload(fileName, file);

      if (uploadError) throw new Error(uploadError.message);

      const { data: urlData } = supabase.storage
        .from("receipts")
        .getPublicUrl(data.path);

      const receipt = await apiFetch(`/api/groups/${groupId}/receipts`, {
        method: "POST",
        body: JSON.stringify({ image_url: urlData.publicUrl }),
      });

      router.push(`/receipts/${receipt.id}`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setError(message);
      setUploading(false);
    }
  };

  return (
    <AuthGuard>
      <div className="mx-auto max-w-2xl px-4 py-6 animate-page">
        <h1 className="mb-6 text-2xl font-bold text-stone-900">Upload Receipt</h1>

        {error && (
          <div className="mb-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-600">{error}</div>
        )}

        {preview ? (
          <div className="space-y-4">
            <img src={preview} alt="Receipt preview" className="w-full rounded-xl border border-stone-200" />
            {uploading && (
              <div className="text-center">
                <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
                <p className="mt-2 text-sm text-stone-500">Uploading and processing...</p>
              </div>
            )}
          </div>
        ) : (
          <div
            onClick={() => fileInputRef.current?.click()}
            className="cursor-pointer rounded-2xl border-2 border-dashed border-stone-300 p-12 text-center hover:border-emerald-400 transition-colors"
          >
            <div className="text-4xl text-stone-400 mb-2">&#128247;</div>
            <p className="text-stone-500">Tap to take a photo or select an image</p>
            <p className="mt-1 text-sm text-stone-400">Supports JPG, PNG, HEIC</p>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileChange}
          className="hidden"
        />
      </div>
    </AuthGuard>
  );
}
