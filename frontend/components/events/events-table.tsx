import type { VisionEvent } from "@/types/api";

type EventsTableProps = {
  events: VisionEvent[];
};

export function EventsTable({ events }: EventsTableProps) {
  return (
    <div className="overflow-hidden rounded-md border border-line bg-white">
      <table className="w-full border-collapse text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase text-muted">
          <tr>
            <th className="px-4 py-3 font-semibold">ID</th>
            <th className="px-4 py-3 font-semibold">Event Type</th>
            <th className="px-4 py-3 font-semibold">Camera</th>
            <th className="px-4 py-3 font-semibold">Severity</th>
            <th className="px-4 py-3 font-semibold">Status</th>
            <th className="px-4 py-3 font-semibold">Created</th>
          </tr>
        </thead>
        <tbody>
          {events.length === 0 ? (
            <tr>
              <td className="px-4 py-10 text-center text-muted" colSpan={6}>
                No events to display.
              </td>
            </tr>
          ) : (
            events.map((event) => (
              <tr key={event.id} className="border-b border-line last:border-0">
                <td className="px-4 py-3 text-slate-600">{event.id}</td>
                <td className="px-4 py-3 font-medium text-ink">{event.event_type}</td>
                <td className="px-4 py-3 text-slate-600">{event.camera_id}</td>
                <td className="px-4 py-3 text-slate-600">{event.severity ?? "-"}</td>
                <td className="px-4 py-3 text-slate-600">{event.status ?? "-"}</td>
                <td className="px-4 py-3 text-slate-600">
                  {new Date(event.created_at).toLocaleString()}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
