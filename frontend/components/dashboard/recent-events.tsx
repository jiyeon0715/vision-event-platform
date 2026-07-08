"use client";

import { useEffect, useState } from "react";

import { EventsTable } from "@/components/events/events-table";
import { getEvents } from "@/lib/api";
import type { VisionEvent } from "@/types/api";

type LoadState = "loading" | "ok" | "error";

export function RecentEvents() {
  const [state, setState] = useState<LoadState>("loading");
  const [events, setEvents] = useState<VisionEvent[]>([]);

  useEffect(() => {
    let cancelled = false;

    getEvents({ page: 1, limit: 5 })
      .then((response) => {
        if (cancelled) return;
        setEvents(response.items);
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
      <p className="mb-3 text-sm font-medium text-muted">Recent Events</p>
      {state === "loading" && (
        <div className="rounded-md border border-line bg-white p-5 text-sm text-slate-500">
          Loading events...
        </div>
      )}
      {state === "error" && (
        <div className="rounded-md border border-line bg-white p-5 text-sm text-red-600">
          Failed to load events.
        </div>
      )}
      {state === "ok" && <EventsTable events={events} />}
    </div>
  );
}
