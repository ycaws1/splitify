export default function DashboardLoading() {
  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div className="h-8 w-32 animate-pulse rounded-lg bg-stone-200" />
        <div className="h-10 w-28 animate-pulse rounded-xl bg-stone-200" />
      </div>
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 animate-pulse rounded-xl bg-stone-200" />
        ))}
      </div>
    </div>
  );
}
