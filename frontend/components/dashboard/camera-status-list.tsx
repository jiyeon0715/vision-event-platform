"use client";

import { useEffect, useState } from "react";

import { CameraList } from "@/components/cameras/camera-list";
import { getCameras } from "@/lib/api";
import type { Camera } from "@/types/api";

type LoadState = "loading" | "ok" | "error";

export function CameraStatusList() {
  const [state, setState] = useState<LoadState>("loading");
  const [cameras, setCameras] = useState<Camera[]>([]);

  useEffect(() => {
    let cancelled = false;

    getCameras({ page: 1, limit: 100 })
      .then((response) => {
        if (cancelled) return;
        setCameras(response.items);
        setState("ok");
      })
      .catch(() => {
        if (!cancelled) setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <p className="mb-3 text-sm font-medium text-muted">Camera Status</p>
      {state === "loading" && (
        <div className="rounded-md border border-line bg-white p-5 text-sm text-slate-500">
          Loading cameras...
        </div>
      )}
      {state === "error" && (
        <div className="rounded-md border border-line bg-white p-5 text-sm text-red-600">
          Failed to load cameras.
        </div>
      )}
      {state === "ok" && <CameraList cameras={cameras} />}
    </div>
  );
}
