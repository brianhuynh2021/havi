"use client";
import { useLanguage } from "@/lib/i18n/language-context";

import { useCallback, useEffect, useRef, useState } from "react";
import { ConnectionCard } from "./connection-card";
import {
  isUsable,
  listConnections,
  PILOT_PLATFORMS,
  readCallbackOutcome,
  type CallbackOutcome,
  type OAuthReturnTarget,
  type PlatformConnection,
} from "./connections.api";
import styles from "./connections.module.css";

type Props = {
  /** Màn đang đứng, để cấp quyền xong backend đưa về đúng đây. */
  returnTo: OAuthReturnTarget;
  /** Gọi mỗi khi danh sách đổi, để màn ngoài biết đã có ≥1 kênh dùng được
   * (onboarding bước 2 mở nút "Tiếp tục" theo cái này). */
  onUsableChange?: (hasUsable: boolean) => void;
};

/**
 * Danh sách kênh + xử lý kết quả quay về từ OAuth.
 *
 * Nguồn sự thật là `GET /connections`, không phải state trong React: chủ tiệm
 * rời khỏi trang sang Facebook rồi quay lại bằng một page load mới, nên mọi
 * `useState` trước đó đã mất. Nối thành công hay không chỉ đọc được từ backend.
 */
export function ConnectionList({ returnTo, onUsableChange }: Props) {
  const {
    t
  } = useLanguage();

  const [connections, setConnections] = useState<PlatformConnection[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const onUsableChangeRef = useRef(onUsableChange);

  useEffect(() => {
    onUsableChangeRef.current = onUsableChange;
  }, [onUsableChange]);

  // Kết quả OAuth đọc được ngay ở lần render đầu — nó nằm trong URL, không phải
  // thứ phải đi hỏi ai. Dùng initializer chứ không effect + setState: đọc trong
  // effect thì khung hình đầu hiện thiếu banner rồi mới nhảy vào.
  const [outcome] = useState<CallbackOutcome>(() =>
    typeof window === "undefined"
      ? null
      : readCallbackOutcome(window.location.search),
  );

  const load = useCallback(async () => {
    const result = await listConnections();
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setError(null);
    setConnections(result.data);
    onUsableChangeRef.current?.(result.data.some((c) => isUsable(c)));
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function initial() {
      const result = await listConnections();
      if (cancelled) return;
      if (!result.ok) {
        setError(result.message);
        return;
      }
      setConnections(result.data);
      onUsableChangeRef.current?.(result.data.some((c) => isUsable(c)));
    }
    initial();
    return () => {
      cancelled = true;
    };
  }, []);

  // Tự động thông báo cho cửa sổ chính và đóng popup nếu đang trong cửa sổ popup OAuth
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.opener && window.opener !== window) {
      const search = window.location.search;
      if (search.includes("ket_noi=")) {
        try {
          window.opener.postMessage({ type: "havi:oauth_complete" }, window.location.origin);
        } catch {
          // Bỏ qua lỗi cross-origin nếu có
        }
        setTimeout(() => {
          window.close();
        }, 400);
      }
    }
  }, []);

  // Lắng nghe tín hiệu kết nối xong từ popup để cập nhật ngay danh sách kênh
  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      if (event.data?.type === "havi:oauth_complete") {
        void load();
      }
    }
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [load]);

  // Xoá `?ket_noi=...` khỏi URL sau khi đã đọc: để nguyên thì chủ tiệm bấm F5
  // lại thấy "Đã nối kênh" dù lần đó chẳng nối gì, và link dán cho người khác
  // cũng mang theo thông báo sai. Chỉ đụng vào URL (hệ thống bên ngoài React),
  // không setState — nên nằm trong effect là đúng chỗ.
  useEffect(() => {
    const url = new URL(window.location.href);
    if (!url.searchParams.has("ket_noi")) return;
    url.searchParams.delete("ket_noi");
    url.searchParams.delete("ly_do");
    window.history.replaceState({}, "", url.toString());
  }, []);

  const byPlatform = new Map(connections?.map((c) => [c.platform, c]) ?? []);

  return (
    <div>
      {outcome?.kind === "ok" ? (
        <p className={`${styles.notice} ${styles.noticeOk}`} role="status">{t("Đã nối kênh xong — Havi đăng bài giúp bạn được rồi.")}</p>
      ) : null}
      {outcome?.kind === "error" ? (
        <p className={`${styles.notice} ${styles.noticeError}`} role="alert">
          {outcome.message}
        </p>
      ) : null}

      {error ? (
        <p className={`${styles.notice} ${styles.noticeError}`} role="alert">
          {error}
        </p>
      ) : null}

      <div className={styles.list}>
        {PILOT_PLATFORMS.map(({ platform, label }) => (
          <ConnectionCard
            key={platform}
            platform={platform}
            label={label}
            connection={byPlatform.get(platform)}
            returnTo={returnTo}
            onChanged={load}
          />
        ))}
      </div>
    </div>
  );
}
