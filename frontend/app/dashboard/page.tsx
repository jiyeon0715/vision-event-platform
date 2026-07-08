import { ContentLayout } from "@/components/layout/content-layout";
import { StatsOverview } from "@/components/dashboard/stats-overview";
import { BackendStatus } from "@/components/dashboard/backend-status";
import { RecentEvents } from "@/components/dashboard/recent-events";
import { CameraStatusList } from "@/components/dashboard/camera-status-list";

export default function DashboardPage() {
  return (
    <ContentLayout title="Dashboard" description="Operational summary">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatsOverview />
        <BackendStatus />
      </div>
      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <RecentEvents />
        <CameraStatusList />
      </div>
    </ContentLayout>
  );
}
