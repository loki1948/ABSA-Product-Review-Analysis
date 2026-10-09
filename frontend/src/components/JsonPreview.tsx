/**
 * Scaffold helper: prints raw API data so each page proves its connection to
 * the backend. Replace every use of it with real UI, then delete this file.
 */
export default function JsonPreview({ data }: { data: unknown }) {
  return (
    <pre className="overflow-x-auto rounded-md border border-slate-200 bg-white p-4 text-xs leading-relaxed">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}
