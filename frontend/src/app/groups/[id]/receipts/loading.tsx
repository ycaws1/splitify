export default function ReceiptListLoading() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <div className="h-8 w-28 animate-pulse rounded-lg bg-stone-200" />
        <div className="h-10 w-32 animate-pulse rounded-xl bg-stone-200" />
      </div>
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 animate-pulse rounded-xl bg-stone-200" />
        ))}
      </div>
    </div>
  );
}
