export default function GroupDetailLoading() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="h-8 w-40 animate-pulse rounded-lg bg-stone-200" />
        <div className="h-10 w-24 animate-pulse rounded-xl bg-stone-200" />
      </div>
      <div className="h-20 animate-pulse rounded-2xl bg-stone-200" />
      <div className="space-y-2">
        <div className="h-6 w-28 animate-pulse rounded bg-stone-200" />
        {[1, 2].map((i) => (
          <div key={i} className="h-14 animate-pulse rounded-xl bg-stone-200" />
        ))}
      </div>
      <div className="h-10 animate-pulse rounded-xl bg-stone-200" />
      <div className="space-y-2">
        <div className="h-6 w-24 animate-pulse rounded bg-stone-200" />
        {[1, 2].map((i) => (
          <div key={i} className="h-14 animate-pulse rounded-xl bg-stone-200" />
        ))}
      </div>
    </div>
  );
}
