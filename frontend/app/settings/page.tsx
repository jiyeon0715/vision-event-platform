import { ContentLayout } from "@/components/layout/content-layout";

export default function SettingsPage() {
  return (
    <ContentLayout title="Settings" description="Dashboard configuration">
      <section className="rounded-md border border-line bg-white p-5">
        <p className="text-sm text-muted">No settings available.</p>
      </section>
    </ContentLayout>
  );
}
