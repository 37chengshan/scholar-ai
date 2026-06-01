/**
 * Page-level Skeleton components
 *
 * Each skeleton matches the layout of its corresponding page to prevent CLS.
 * Built on top of the shadcn Skeleton primitive (ui/skeleton.tsx).
 */

import { Skeleton } from "@/app/components/ui/skeleton";

/** Search results page skeleton: filter sidebar + result cards */
export function SearchResultsSkeleton() {
  return (
    <div className="flex h-full">
      {/* Sidebar filters */}
      <div className="hidden w-64 shrink-0 border-r border-border/50 p-4 space-y-4 md:block">
        <Skeleton className="h-5 w-24" />
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
        <Skeleton className="h-5 w-20 mt-4" />
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      </div>

      {/* Result cards */}
      <div className="flex-1 p-4 space-y-4">
        <Skeleton className="h-10 w-full" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-border/50 p-4 space-y-3">
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <div className="flex gap-2">
              <Skeleton className="h-6 w-16" />
              <Skeleton className="h-6 w-20" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Knowledge base detail skeleton: three-column layout */
export function KnowledgeBaseSkeleton() {
  return (
    <div className="flex h-full">
      {/* Left: KB info */}
      <div className="w-72 shrink-0 border-r border-border/50 p-4 space-y-4">
        <Skeleton className="h-6 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <div className="space-y-2 mt-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      </div>

      {/* Center: paper list */}
      <div className="flex-1 p-4 space-y-3">
        <Skeleton className="h-10 w-full" />
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 p-3 rounded-lg border border-border/50">
            <Skeleton className="h-10 w-10 rounded" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
        ))}
      </div>

      {/* Right: preview */}
      <div className="hidden w-80 shrink-0 border-l border-border/50 p-4 space-y-3 xl:block">
        <Skeleton className="h-5 w-1/2" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    </div>
  );
}

/** Analytics dashboard skeleton: metric cards + chart area */
export function AnalyticsSkeleton() {
  return (
    <div className="p-4 space-y-6">
      {/* Metric cards row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-border/50 p-4 space-y-2">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-3 w-1/3" />
          </div>
        ))}
      </div>

      {/* Chart area */}
      <div className="rounded-xl border border-border/50 p-4">
        <Skeleton className="h-5 w-32 mb-4" />
        <Skeleton className="h-64 w-full" />
      </div>

      {/* Bottom section */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-border/50 p-4 space-y-3">
          <Skeleton className="h-5 w-24" />
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
        <div className="rounded-xl border border-border/50 p-4 space-y-3">
          <Skeleton className="h-5 w-28" />
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      </div>
    </div>
  );
}

/** Read page skeleton: document viewer with optional sidebar */
export function ReadSkeleton() {
  return (
    <div className="flex h-full">
      {/* Sidebar: document outline / TOC */}
      <div className="hidden w-64 shrink-0 border-r border-border/50 p-4 space-y-3 md:block">
        <Skeleton className="h-5 w-20" />
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-4 w-full" />
          ))}
        </div>
        <Skeleton className="h-5 w-16 mt-4" />
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-4 w-5/6" />
          ))}
        </div>
      </div>

      {/* Main content: paper body */}
      <div className="flex-1 p-6 space-y-4 max-w-3xl mx-auto">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-4 w-1/3" />
        <div className="space-y-3 mt-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-4 w-full" />
          ))}
        </div>
        <Skeleton className="h-32 w-full mt-4" />
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-4 w-full" />
          ))}
        </div>
      </div>
    </div>
  );
}

/** Compare page skeleton: sidebar + main panel + inspector */
export function CompareSkeleton() {
  return (
    <div className="flex h-full">
      {/* Sidebar: paper selection */}
      <div className="w-64 shrink-0 border-r border-border/50 p-4 space-y-3">
        <Skeleton className="h-10 w-full" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-border/50 p-3 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-full" />
          </div>
        ))}
      </div>

      {/* Main: comparison grid */}
      <div className="flex-1 p-4 space-y-4">
        <Skeleton className="h-10 w-full" />
        <div className="grid grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border/50 p-4 space-y-3">
              <Skeleton className="h-5 w-1/2" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** Notes page skeleton: note list + editor area */
export function NotesSkeleton() {
  return (
    <div className="flex h-full">
      {/* Note list */}
      <div className="w-72 shrink-0 border-r border-border/50 p-4 space-y-3">
        <Skeleton className="h-10 w-full" />
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-border/50 p-3 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-1/3" />
          </div>
        ))}
      </div>

      {/* Editor area */}
      <div className="flex-1 p-6 space-y-4">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-4 w-1/4" />
        <div className="space-y-3 mt-6">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      </div>
    </div>
  );
}
