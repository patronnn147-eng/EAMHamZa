export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-24 rounded-lg bg-slate-800 animate-pulse" />
        ))}
      </div>
      <div className="h-40 rounded-lg bg-slate-800 animate-pulse" />
    </div>
  );
}
