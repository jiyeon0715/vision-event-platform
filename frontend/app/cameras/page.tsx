import { CameraList } from "@/components/cameras/camera-list";
import { ContentLayout } from "@/components/layout/content-layout";
import { getCameras } from "@/lib/api";
import type { Camera } from "@/types/api";

async function loadCameras(): Promise<Camera[]> {
  try {
    const response = await getCameras({ page: 1, limit: 100 });
    return response.items;
  } catch {
    return [];
  }
}

export default async function CamerasPage() {
  const cameras = await loadCameras();

  return (
    <ContentLayout title="Cameras" description="Configured camera sources">
      <CameraList cameras={cameras} />
    </ContentLayout>
  );
}
