/**
 * Nơi duy nhất đọc/ghi token. Mọi thứ khác phải đi qua đây.
 *
 * Đang dùng localStorage: đơn giản, không cần backend đổi gì. Đánh đổi là XSS
 * đọc được refresh token — chấp nhận ở pilot, nhưng vì mọi truy cập token đều
 * qua module này nên đổi sang httpOnly cookie sau chỉ phải sửa một file.
 *
 * Không bao giờ log token ra console (ROADMAP §7 Definition of Done).
 */

const STORAGE_KEY = "havi.tokens";

export type StoredTokens = {
  accessToken: string;
  refreshToken: string;
  activeWorkspaceId: string | null;
  needsOnboarding: boolean;
};

/** SSR không có localStorage — trả null thay vì ném, để layout render được. */
function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    // Safari private mode ném khi truy cập localStorage.
    return null;
  }
}

/** Cache bản đã parse để `subscribe`/`getSnapshot` của useSyncExternalStore trả
 * cùng một reference khi dữ liệu không đổi — trả object mới mỗi lần đọc sẽ làm
 * React render vô hạn. */
let cachedRaw: string | null = null;
let cachedTokens: StoredTokens | null = null;

export function readTokens(): StoredTokens | null {
  const raw = storage()?.getItem(STORAGE_KEY) ?? null;
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    cachedTokens = raw ? parseTokens(raw) : null;
  }
  syncCookie(Boolean(cachedTokens));
  return cachedTokens;
}

function parseTokens(raw: string): StoredTokens | null {
  try {
    const parsed = JSON.parse(raw) as Partial<StoredTokens>;
    // Dữ liệu cũ/hỏng thì coi như chưa đăng nhập, không để app chạy với token
    // nửa vời rồi lỗi 401 ở chỗ khác khó truy.
    if (!parsed.accessToken || !parsed.refreshToken) return null;
    return {
      accessToken: parsed.accessToken,
      refreshToken: parsed.refreshToken,
      activeWorkspaceId: parsed.activeWorkspaceId ?? null,
      needsOnboarding: parsed.needsOnboarding ?? false,
    };
  } catch {
    return null;
  }
}

const listeners = new Set<() => void>();

/** Đăng ký nghe thay đổi token. Có cả `storage` event để đăng xuất ở tab này
 * kéo theo tab kia — chủ tiệm hay mở nhiều tab, để một tab còn tưởng đang đăng
 * nhập rồi ăn 401 là trạng thái khó hiểu. */
export function subscribeTokens(listener: () => void): () => void {
  listeners.add(listener);
  const onStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY || event.key === null) listener();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

function notify(): void {
  for (const listener of listeners) listener();
}

function syncCookie(hasTokens: boolean): void {
  if (typeof document === "undefined") return;
  if (hasTokens) {
    document.cookie = "havi_session=1; path=/; max-age=2592000; SameSite=Lax";
  } else {
    document.cookie = "havi_session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  }
}

export function writeTokens(tokens: StoredTokens): void {
  storage()?.setItem(STORAGE_KEY, JSON.stringify(tokens));
  syncCookie(true);
  notify();
}

export function clearTokens(): void {
  storage()?.removeItem(STORAGE_KEY);
  syncCookie(false);
  notify();
}
