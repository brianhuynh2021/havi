"use client";

import { useEffect, useState } from "react";
import {
  isUsable,
  listConnections,
  type PlatformConnection,
} from "@/features/connections/connections.api";
import styles from "./app-shell.module.css";

const PLATFORM_LABELS: Record<string, string> = {
  facebook: "Facebook",
  google_business: "Google Maps SEO",
  tiktok: "TikTok",
  youtube: "YouTube Shorts",
  zalo_oa: "Zalo OA",
};

/**
 * Chip kênh đã nối trong thẻ workspace.
 *
 * Trước đây đây là một mảng hằng `["Facebook", "TikTok", "Zalo", "Maps"]` — tức
 * là chủ tiệm nào cũng thấy bốn kênh "đã nối" dù chưa nối gì, và ba trong bốn
 * kênh đó Havi còn chưa có adapter. Đúng thứ ROADMAP Tuần 7 cấm: "Không hiển thị
 * TikTok/Zalo/Maps là 'đã nối' nếu chỉ là fixture".
 *
 * Chỉ hiện kênh `connected`. Kênh hết hạn/mất quyền không được tính là đã nối:
 * chấm xanh trong lúc bài đang hỏng là thông tin sai ở đúng chỗ nguy hiểm nhất.
 */
export function WorkspaceChannels() {
  const [connections, setConnections] = useState<PlatformConnection[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    listConnections().then((result) => {
      if (!cancelled && result.ok) setConnections(result.data);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Chưa tải xong thì không hiện gì: hiện "Chưa nối kênh" trong một phần giây
  // rồi nhảy sang "Facebook" là nháy khó chịu, và trên 4G thì kéo dài đủ lâu để
  // chủ tiệm đọc được câu sai.
  if (connections === null) return null;

  const usable = connections.filter(isUsable);
  if (usable.length === 0) {
    return (
      <div className={styles.workspaceChips}>
        <span className={styles.workspaceChipUnconnected}>
          ⚪ Chưa kết nối Fanpage
        </span>
      </div>
    );
  }

  return (
    <div className={styles.workspaceChips}>
      {usable.map((connection) => (
        <span key={connection.platform} className={styles.workspaceChip}>
          <span className={styles.livePulseDot} />
          {PLATFORM_LABELS[connection.platform] ?? connection.platform}
        </span>
      ))}
    </div>
  );
}
