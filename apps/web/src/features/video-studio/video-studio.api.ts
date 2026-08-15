import { readTokens } from "@/lib/auth/token-store";
import { NETWORK_ERROR_MESSAGE, detailToMessage } from "@/features/auth/auth.api";

export type VideoRenderStatus = "queued" | "rendering" | "completed" | "failed" | "cancelled";
export type VideoRenderEngine = "ffmpeg" | "remotion";
export type VideoCaptionStyle = "bold_yellow" | "clean_white" | "neon_cyan" | "boxed_black";

export type VideoCut = {
  start_ms: number;
  end_ms: number;
  zoom_scale?: number;
  transition?: string;
};

export type VideoCaption = {
  text: string;
  start_ms: number;
  end_ms: number;
  style?: VideoCaptionStyle;
  position_y?: number;
};

export type VideoAudioConfig = {
  normalize_db?: number;
  bg_music_volume?: number;
  voiceover_volume?: number;
};

export type EditPlan = {
  target_aspect_ratio: "9:16" | "1:1" | "16:9";
  target_duration_seconds: number;
  cuts: VideoCut[];
  captions: VideoCaption[];
  audio?: VideoAudioConfig;
};

export type VideoRenderJob = {
  id: string;
  workspace_id: string;
  title: string;
  target_aspect_ratio: string;
  status: VideoRenderStatus;
  progress_percent: number;
  renderer_engine: VideoRenderEngine;
  source_media_id: string | null;
  edit_plan: EditPlan;
  output_media_id: string | null;
  output_url: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
};

export type CreateRenderJobPayload = {
  title: string;
  target_aspect_ratio?: "9:16" | "1:1" | "16:9";
  edit_plan?: EditPlan;
  source_media_id?: string | null;
  renderer_engine?: VideoRenderEngine;
};

export type ListRenderJobsResponse = {
  items: VideoRenderJob[];
  total: number;
  limit: number;
  offset: number;
};

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const GENERIC_ERROR = "Không thể kết nối đến máy chủ render video.";

function getAuthHeaders(): HeadersInit {
  const tokens = readTokens();
  return {
    "Content-Type": "application/json",
    ...(tokens?.accessToken ? { Authorization: `Bearer ${tokens.accessToken}` } : {}),
  };
}

export function getActiveWorkspaceId(): string | null {
  return readTokens()?.activeWorkspaceId ?? null;
}

export async function listRenderJobs(
  workspaceId: string,
  options?: { status?: VideoRenderStatus; limit?: number; offset?: number },
): Promise<Result<ListRenderJobsResponse>> {
  try {
    const params = new URLSearchParams();
    if (options?.status) params.set("status", options.status);
    if (options?.limit) params.set("limit", options.limit.toString());
    if (options?.offset) params.set("offset", options.offset.toString());

    const queryStr = params.toString() ? `?${params.toString()}` : "";
    const res = await fetch(
      `${baseUrl}/workspaces/${workspaceId}/video/render-jobs${queryStr}`,
      {
        headers: getAuthHeaders(),
      },
    );

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return { ok: false, message: detailToMessage(err.detail, GENERIC_ERROR) };
    }

    const data: ListRenderJobsResponse = await res.json();
    return { ok: true, data };
  } catch (error) {
    if (error instanceof TypeError) {
      return { ok: false, message: NETWORK_ERROR_MESSAGE };
    }
    return { ok: false, message: GENERIC_ERROR };
  }
}

export async function getRenderJob(
  workspaceId: string,
  jobId: string,
): Promise<Result<VideoRenderJob>> {
  try {
    const res = await fetch(
      `${baseUrl}/workspaces/${workspaceId}/video/render-jobs/${jobId}`,
      {
        headers: getAuthHeaders(),
      },
    );

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return { ok: false, message: detailToMessage(err.detail, GENERIC_ERROR) };
    }

    const data: VideoRenderJob = await res.json();
    return { ok: true, data };
  } catch (error) {
    if (error instanceof TypeError) {
      return { ok: false, message: NETWORK_ERROR_MESSAGE };
    }
    return { ok: false, message: GENERIC_ERROR };
  }
}

export async function createRenderJob(
  workspaceId: string,
  payload: CreateRenderJobPayload,
): Promise<Result<VideoRenderJob>> {
  try {
    const res = await fetch(`${baseUrl}/workspaces/${workspaceId}/video/render-jobs`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return { ok: false, message: detailToMessage(err.detail, GENERIC_ERROR) };
    }

    const data: VideoRenderJob = await res.json();
    return { ok: true, data };
  } catch (error) {
    if (error instanceof TypeError) {
      return { ok: false, message: NETWORK_ERROR_MESSAGE };
    }
    return { ok: false, message: GENERIC_ERROR };
  }
}

export async function retryRenderJob(
  workspaceId: string,
  jobId: string,
): Promise<Result<VideoRenderJob>> {
  try {
    const res = await fetch(
      `${baseUrl}/workspaces/${workspaceId}/video/render-jobs/${jobId}/retry`,
      {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({}),
      },
    );

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return { ok: false, message: detailToMessage(err.detail, GENERIC_ERROR) };
    }

    const data: VideoRenderJob = await res.json();
    return { ok: true, data };
  } catch (error) {
    if (error instanceof TypeError) {
      return { ok: false, message: NETWORK_ERROR_MESSAGE };
    }
    return { ok: false, message: GENERIC_ERROR };
  }
}

export async function cancelRenderJob(
  workspaceId: string,
  jobId: string,
): Promise<Result<{ ok: boolean }>> {
  try {
    const res = await fetch(
      `${baseUrl}/workspaces/${workspaceId}/video/render-jobs/${jobId}/cancel`,
      {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({}),
      },
    );

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return { ok: false, message: detailToMessage(err.detail, GENERIC_ERROR) };
    }

    const data: { ok: boolean } = await res.json();
    return { ok: true, data };
  } catch (error) {
    if (error instanceof TypeError) {
      return { ok: false, message: NETWORK_ERROR_MESSAGE };
    }
    return { ok: false, message: GENERIC_ERROR };
  }
}
