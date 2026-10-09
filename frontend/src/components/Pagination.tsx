interface Props {
  /** 1-based page number. */
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}

const button =
  "rounded-md border border-slate-300 bg-white px-3 py-1 text-sm hover:border-blue-600 disabled:cursor-not-allowed disabled:opacity-50";

export default function Pagination({ page, pageSize, total, onChange }: Props) {
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);
  return (
    <nav aria-label="Pages" className="flex items-center justify-between gap-3 text-sm text-slate-600">
      <span className="tabular-nums">
        {first}–{last} of {total}
      </span>
      <div className="flex gap-2">
        <button type="button" className={button} disabled={page <= 1} onClick={() => onChange(page - 1)}>
          Previous
        </button>
        <button type="button" className={button} disabled={last >= total} onClick={() => onChange(page + 1)}>
          Next
        </button>
      </div>
    </nav>
  );
}
