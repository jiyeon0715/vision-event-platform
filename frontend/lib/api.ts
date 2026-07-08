import type {
  Camera,
  EventStats,
  EventType,
  ListCamerasParams,
  ListEventsParams,
  ListEventTypesParams,
  PaginatedResponse,
  VisionEvent,
} from "@/types/api";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? DEFAULT_API_BASE_URL;

const API_KEY = process.env.NEXT_PUBLIC_API_KEY;

type QueryParams = Record<string, string | number | boolean | undefined>;

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function buildUrl(path: string, params?: QueryParams) {
  const url = new URL(`${API_BASE_URL}${path}`);

  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });

  return url;
}

async function request<T>(
  path: string,
  params?: QueryParams,
): Promise<T> {
  const response = await fetch(buildUrl(path, params), {
    headers: {
      Accept: "application/json",
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(response.status, `API request failed: ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export function getEvents(params: ListEventsParams = {}) {
  return request<PaginatedResponse<VisionEvent>>("/events", params as QueryParams);
}

export function getEventStats(params: ListEventsParams = {}) {
  return request<EventStats>("/events/stats", params as QueryParams);
}

export function getCameras(params: ListCamerasParams = {}) {
  return request<PaginatedResponse<Camera>>("/cameras", params as QueryParams);
}

export function getEventTypes(params: ListEventTypesParams = {}) {
  return request<PaginatedResponse<EventType>>("/event-types", params as QueryParams);
}

export { ApiError };
