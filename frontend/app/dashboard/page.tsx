import { ContentLayout } from "@/components/layout/content-layout";
import { StatCard } from "@/components/dashboard/stat-card";
import { BackendStatus } from "@/components/dashboard/backend-status";

const cards = [
  {
    label: "Total Events",
    value: "0",
    helper: "No events recorded",
  },
  {
    label: "Cameras",
    value: "0",
    helper: "No sources configured",
  },
  {
    label: "Event Types",
    value: "0",
    helper: "No active types",
  },
  {
    label: "Snapshots",
    value: "0",
    helper: "No snapshots available",
  },
];

export default function DashboardPage() {
  return (
    <ContentLayout title="Dashboard" description="Operational summary">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <StatCard key={card.label} {...card} />
        ))}
        <BackendStatus />
      </div>
    </ContentLayout>
  );
}
