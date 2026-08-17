import { readTokens } from "@/lib/auth/token-store";

export type VoiceTranscribeResult = {
  text: string;
  summary: string;
  detected_intent: string;
};

export type VoiceToContentResult = {
  text: string;
  summary: string;
  detected_intent: string;
  job_id: string;
  job_status: string;
};

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; message: string; status: number };

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function authedRequest(path: string, init: RequestInit): Promise<Response> {
  const tokens = readTokens();
  const headers = new Headers(init.headers || {});
  if (tokens?.accessToken) {
    headers.set("Authorization", `Bearer ${tokens.accessToken}`);
  }
  return fetch(`${baseUrl}${path}`, {
    ...init,
    headers,
  });
}

export async function transcribeVoice(
  audioBase64: string,
  mimeType: string = "audio/webm",
): Promise<ApiResult<VoiceTranscribeResult>> {
  try {
    const res = await authedRequest("/voice/transcribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        audio_base64: audioBase64,
        mime_type: mimeType,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return {
        ok: false,
        message: err.detail || "Không thể nhận diện giọng nói. Vui lòng thử lại.",
        status: res.status,
      };
    }

    const data = await res.json();
    return { ok: true, data };
  } catch {
    return {
      ok: false,
      message: "Lỗi kết nối máy chủ khi chuyển giọng nói.",
      status: 0,
    };
  }
}

export async function voiceToContent(
  audioBase64: string,
  mimeType: string = "audio/webm",
): Promise<ApiResult<VoiceToContentResult>> {
  try {
    const res = await authedRequest("/voice/voice-to-content", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        audio_base64: audioBase64,
        mime_type: mimeType,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return {
        ok: false,
        message: err.detail || "Không thể tạo bài từ giọng nói. Vui lòng thử lại.",
        status: res.status,
      };
    }

    const data = await res.json();
    return { ok: true, data };
  } catch {
    return {
      ok: false,
      message: "Lỗi kết nối máy chủ khi tạo bài từ giọng nói.",
      status: 0,
    };
  }
}
