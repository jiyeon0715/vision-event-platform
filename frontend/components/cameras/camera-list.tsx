import type { Camera } from "@/types/api";

type CameraListProps = {
  cameras: Camera[];
};

export function CameraList({ cameras }: CameraListProps) {
  return (
    <div className="rounded-md border border-line bg-white p-5">
      <div className="space-y-3">
        {cameras.length === 0 ? (
          <p className="text-sm text-muted">No cameras to display.</p>
        ) : (
          cameras.map((camera) => (
            <div key={camera.id} className="flex items-center justify-between border-b border-line pb-3 last:border-0 last:pb-0">
              <div>
                <p className="font-medium text-ink">{camera.name}</p>
                <p className="text-sm text-muted">{camera.source_type}</p>
              </div>
              <span className="text-sm text-slate-600">{camera.status}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
