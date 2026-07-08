import { EventsTable } from "@/components/events/events-table";
import { ContentLayout } from "@/components/layout/content-layout";
import { getEvents } from "@/lib/api";
import type { VisionEvent } from "@/types/api";

async function loadEvents(): Promise<VisionEvent[]> {
  try {
    const response = await getEvents({ page: 1, limit: 50 });
    return response.items;
  } catch {
    return [];
  }
}

export default async function EventsPage() {
  const events = await loadEvents();

  return (
    <ContentLayout title="Events" description="Recent vision events">
      <EventsTable events={events} />
    </ContentLayout>
  );
}
