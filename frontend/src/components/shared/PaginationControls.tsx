interface PaginationControlsProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export default function PaginationControls({ page, totalPages, onPageChange }: PaginationControlsProps) {
  return (
    <div className="flex items-center justify-center gap-3 pt-4">
      <button
        type="button"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        className="px-4 py-1.5 rounded-lg text-xs font-semibold border border-[var(--line)] bg-[var(--surface)] text-[var(--text)] hover:border-[var(--purple)] disabled:opacity-40 disabled:cursor-not-allowed transition-all"
      >
        ← Previous
      </button>
      <span className="text-xs text-[var(--muted)]">
        Page {page} of {totalPages}
      </span>
      <button
        type="button"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
        className="px-4 py-1.5 rounded-lg text-xs font-semibold border border-[var(--line)] bg-[var(--surface)] text-[var(--text)] hover:border-[var(--purple)] disabled:opacity-40 disabled:cursor-not-allowed transition-all"
      >
        Next →
      </button>
    </div>
  );
}
