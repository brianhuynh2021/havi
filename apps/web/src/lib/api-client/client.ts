import createClient from "openapi-fetch";
import type { paths } from "./schema";

// Backend chưa có token session thật (Tuần 4) — baseUrl trỏ local API khi phát triển.
// Frontend không giữ secret/token nền tảng; chỉ JWT của chính user (khi có auth thật).
const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const apiClient = createClient<paths>({ baseUrl });
