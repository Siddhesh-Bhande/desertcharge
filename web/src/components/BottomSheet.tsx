import type { ReactNode } from 'react'

interface BottomSheetProps {
  children: ReactNode
  expandable?: boolean
  expanded?: boolean
  onToggle?: () => void
}

// The floating instrument panel. Registration ticks are the signature detail.
export function BottomSheet({ children, expandable, expanded, onToggle }: BottomSheetProps) {
  return (
    <section
      className="pointer-events-auto relative max-h-[72vh] overflow-y-auto rounded-t-3xl bg-basalt-800/98 px-5 pb-[max(1rem,env(safe-area-inset-bottom))] pt-4 shadow-[0_-8px_40px_rgba(0,0,0,0.45)] backdrop-blur"
      aria-label="Location detail"
    >
      <span className="pointer-events-none absolute left-3 top-2.5 h-2.5 w-2.5 border-l border-t border-bone-100/40" />
      <span className="pointer-events-none absolute right-3 top-2.5 h-2.5 w-2.5 border-r border-t border-bone-100/40" />
      {expandable ? (
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={expanded}
          aria-label={expanded ? 'Collapse details' : 'Expand details'}
          className="mx-auto mb-3.5 block h-1 w-9 rounded-full bg-bone-100/30"
        />
      ) : (
        <div className="mx-auto mb-3.5 h-1 w-9 rounded-full bg-bone-100/30" />
      )}
      {children}
    </section>
  )
}
