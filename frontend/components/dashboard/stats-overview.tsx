"use client";

import { useEffect, useState } from "react";

import { StatCard } from "@/components/dashboard/stat-card";
import { getCameras, getEventStats, getEventTypes } from "@/lib/api";

type StatSlot = {
  value: string;
  helper: string;
};

const LOADING_SLOT: StatSlot = { value: "-", helper: "Loading..." };
const ERROR_SLOT: StatSlot = { value: "-", helper: "Failed to load" };

export function StatsOverview() {
  const [totalEvents, setTotalEvents] = useState<StatSlot>(LOADING_SLOT);
  const [cameras, setCameras] = useState<StatSlot>(LOADING_SLOT);
  const [eventTypes, setEventTypes] = useState<StatSlot>(LOADING_SLOT);

  useEffect(() => {
    let cancelled = false;

    getEventStats()
      .then((stats) => {
        if (cancelled) return;
        setTotalEvents({
          value: String(stats.total_event_count),
          helper:
            stats.total_event_count === 0
              ? "No events recorded"
              : `Latest: ${stats.latest_event_timestamp ?? "-"}`,
        });
      })
      .catch(() => !cancelled && setTotalEvents(ERROR_SLOT));

    getCameras({ page: 1, limit: 1 })
      .then((response) => {
        if (cancelled) return;
        setCameras({
          value: String(response.total),
          helper: response.total === 0 ? "No sources configured" : "Configured sources",
        });
      })
      .catch(() => !cancelled && setCameras(ERROR_SLOT));

    getEventTypes({ page: 1, limit: 1 })
      .then((response) => {
        if (cancelled) return;
        setEventTypes({
          value: String(response.total),
          helper: response.total === 0 ? "No active types" : "Managed types",
        });
      })
      .catch(() => !cancelled && setEventTypes(ERROR_SLOT));

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <StatCard label="Total Events" value={totalEvents.value} helper={totalEvents.helper} />
      <StatCard label="Cameras" value={cameras.value} helper={cameras.helper} />
      <StatCard label="Event Types" value={eventTypes.value} helper={eventTypes.helper} />
    </>
  );
}
