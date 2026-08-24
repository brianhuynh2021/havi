import { readTokens } from "@/lib/auth/token-store";
import { authedFetch } from "@/lib/api-client/client";
import { NETWORK_ERROR_MESSAGE, detailToMessage } from "@/features/auth/auth.api";

export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

export type GoalCategory =
  | "acquire_customers"
  | "sell_offer"
  | "launch"
  | "recruit"
  | "deliver_project"
  | "learn_skill"
  | "grow_audience"
  | "improve_operations"
  | "other";

export type Goal = {
  id: string;
  workspace_id: string;
  title: string;
  description: string | null;
  category: GoalCategory;
  evidence_definition: string;
  target_deadline: string | null;
  weekly_capacity_hours: number;
  constraints: Record<string, unknown> | null;
  status: "active" | "paused" | "completed" | "abandoned";
  created_at: string;
  updated_at: string;
};

export type Roadmap = {
  id: string;
  workspace_id: string;
  goal_id: string;
  version: number;
  title: string;
  horizon_90d: string;
  horizon_30d: string;
  horizon_7d: string;
  assumptions: string[] | null;
  confidence_score: number;
  status: "draft" | "active" | "archived" | "superseded";
  created_at: string;
};

export type RoadmapTask = {
  id: string;
  workspace_id: string;
  roadmap_id: string;
  goal_id: string;
  title: string;
  description: string | null;
  why_this_is_next: string;
  time_estimate_minutes: number;
  owner_type: "user" | "havi" | "collaborative";
  capability_module: string;
  inputs_needed: string | null;
  done_rule: string;
  fallback_action: string | null;
  status: "pending" | "in_progress" | "completed" | "blocked" | "skipped";
  scheduled_date: string | null;
  completed_at: string | null;
  evidence_notes: string | null;
  order_index: number;
  created_at: string;
};

export type ActiveRoadmapData = {
  roadmap: Roadmap;
  tasks: RoadmapTask[];
};

export type EvidenceLog = {
  id: string;
  workspace_id: string;
  goal_id: string;
  task_id: string | null;
  source: string;
  evidence_type: string;
  value_number: number | null;
  value_text: string;
  media_asset_id: string | null;
  confidence: number;
  created_at: string;
};

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchWithAuth(path: string, init?: RequestInit): Promise<Response> {
  const url = path.startsWith("http") ? path : `${baseUrl}${path}`;
  const req = new Request(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  return authedFetch(req);
}

export function getActiveWorkspaceId(): string | null {
  const tokens = readTokens();
  return tokens?.activeWorkspaceId || null;
}

export async function fetchActiveGoal(): Promise<Result<Goal | null>> {
  try {
    const res = await fetchWithAuth("/goals/active");
    if (!res.ok) {
      if (res.status === 404) return { ok: true, data: null };
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không tải được mục tiêu") };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function createGoal(params: {
  title: string;
  category: GoalCategory;
  evidence_definition: string;
  description?: string;
  target_deadline?: string;
  weekly_capacity_hours?: number;
}): Promise<Result<Goal>> {
  try {
    const res = await fetchWithAuth("/goals", {
      method: "POST",
      body: JSON.stringify(params),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không tạo được mục tiêu") };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function deleteGoal(goalId: string): Promise<Result<null>> {
  try {
    const res = await fetchWithAuth(`/goals/${goalId}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không thể đặt lại mục tiêu") };
    }
    return { ok: true, data: null };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}


export async function generateRoadmap(goalId: string): Promise<Result<ActiveRoadmapData>> {
  try {
    const res = await fetchWithAuth("/roadmaps/generate", {
      method: "POST",
      body: JSON.stringify({ goal_id: goalId }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không sinh được lộ trình") };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function fetchActiveRoadmap(): Promise<Result<ActiveRoadmapData | null>> {
  try {
    const res = await fetchWithAuth("/roadmaps/active");
    if (!res.ok) {
      if (res.status === 404) return { ok: true, data: null };
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không tải được lộ trình") };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function fetchTodayAction(): Promise<Result<RoadmapTask | null>> {
  try {
    const res = await fetchWithAuth("/roadmaps/today");
    if (!res.ok) {
      if (res.status === 404) return { ok: true, data: null };
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không tải được việc hôm nay") };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function completeTask(
  taskId: string,
  params: { evidence_text: string; evidence_type?: string; value_number?: number }
): Promise<Result<RoadmapTask>> {
  try {
    const res = await fetchWithAuth(`/roadmaps/tasks/${taskId}/complete`, {
      method: "POST",
      body: JSON.stringify(params),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không hoàn thành được việc") };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function blockTask(
  taskId: string,
  params: { reason: string; use_fallback?: boolean }
): Promise<Result<RoadmapTask>> {
  try {
    const res = await fetchWithAuth(`/roadmaps/tasks/${taskId}/block`, {
      method: "POST",
      body: JSON.stringify(params),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không cập nhật được trạng thái") };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function reopenTask(taskId: string): Promise<Result<RoadmapTask>> {
  try {
    const res = await fetchWithAuth(`/roadmaps/tasks/${taskId}/reopen`, {
      method: "POST",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không mở lại được việc") };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function fetchRoadmapHistory(): Promise<Result<Roadmap[]>> {
  try {
    const res = await fetchWithAuth("/roadmaps/history");
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không tải được lịch sử lộ trình") };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function restoreRoadmap(roadmapId: string): Promise<Result<ActiveRoadmapData>> {
  try {
    const res = await fetchWithAuth(`/roadmaps/${roadmapId}/restore`, {
      method: "POST",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không khôi phục được lộ trình") };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function fetchEvidenceList(): Promise<Result<EvidenceLog[]>> {
  try {
    const res = await fetchWithAuth("/roadmaps/evidence");
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không tải được danh sách bằng chứng") };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export type ReviewRecord = {
  id: string;
  workspace_id: string;
  goal_id: string;
  roadmap_id: string;
  review_date: string;
  completed_summary: string;
  evidence_summary: string;
  obstacles_summary: string;
  decision: "continue" | "improve" | "pivot" | "pause" | "stop";
  replan_diff: Record<string, unknown> | null;
  user_accepted: boolean;
};

export async function fetchReviewList(): Promise<Result<ReviewRecord[]>> {
  try {
    const res = await fetchWithAuth("/roadmaps/reviews");
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không tải được danh sách đánh giá") };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}

export async function createWeeklyReview(
  roadmapId: string,
  params: {
    completed_summary: string;
    evidence_summary: string;
    obstacles_summary: string;
    decision: "continue" | "improve" | "pivot" | "pause" | "stop";
    replan_diff?: Record<string, unknown>;
  }
): Promise<Result<ReviewRecord>> {
  try {
    const res = await fetchWithAuth(`/roadmaps/${roadmapId}/review`, {
      method: "POST",
      body: JSON.stringify(params),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, message: detailToMessage(body?.detail, "Không lưu được đánh giá tuần") };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, message: NETWORK_ERROR_MESSAGE };
  }
}


