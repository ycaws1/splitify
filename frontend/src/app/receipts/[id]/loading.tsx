export default function ReceiptDetailLoading() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-6 space-y-4">
      <div className="h-8 w-48 animate-pulse rounded-lg bg-stone-200" />
      <div className="h-40 animate-pulse rounded-2xl bg-stone-200" />
      <div className="space-y-2">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-16 animate-pulse rounded-xl bg-stone-200" />
        ))}
      </div>
    </div>
  );
}
