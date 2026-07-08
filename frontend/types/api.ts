export type PaginatedResponse<T> = {
  items: T[];
  page: number;
  limit: number;
  total: number;
  total_pages: number;
};

export type EventSeverity = "info" | "warning" | "critical" | string;
export type EventStatus = "new" | "acknowledged" | string;

export type VisionEvent = {
  id: number;
  event_type: string;
  camera_id: string;
  track_id: number;
  timestamp: number;
  message: string;
  severity?: EventSeverity | null;
  status?: EventStatus | null;
  snapshot_path?: string | null;
  created_at: string;
};

export type EventStats = {
  total_event_count: number;
  event_count_by_type: Record<string, number>;
  event_count_by_rule_name: Record<string, number>;
  event_count_by_camera_id: Record<string, number>;
  event_count_by_status: Record<string, number>;
  hourly_event_counts: Record<string, number>;
  latest_event_timestamp: string | null;
};

export type CameraStatus = "active" | "inactive" | "error" | string;
export type CameraSourceType = "image" | "video" | "camera" | "rtsp" | "webcam" | string;

export type Camera = {
  id: number;
  name: string;
  source_type: CameraSourceType;
  source_uri: string;
  location?: string | null;
  status: CameraStatus;
  last_seen_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type EventTypeSeverity = "info" | "warning" | "critical" | string;

export type EventType = {
  id: number;
  key: string;
  name: string;
  description?: string | null;
  default_severity: EventTypeSeverity;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ListEventsParams = {
  page?: number;
  limit?: number;
  camera_id?: string;
  event_type?: string;
  severity?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
};

export type ListCamerasParams = {
  page?: number;
  limit?: number;
  status?: string;
  source_type?: string;
};

export type ListEventTypesParams = {
  page?: number;
  limit?: number;
  is_active?: boolean;
};
