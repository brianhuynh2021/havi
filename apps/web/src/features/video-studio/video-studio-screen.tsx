"use client";

import { useCallback, useEffect, useState } from "react";
import {
  listRenderJobs,
  createRenderJob,
  retryRenderJob,
  cancelRenderJob,
  getActiveWorkspaceId,
  getHotTrends,
  refreshHotTrends,
  type VideoRenderJob,
  type VideoCaptionStyle,
  type TrendingTopic,
} from "./video-studio.api";
import styles from "./video-studio.module.css";

export function VideoStudioScreen() {
  const [jobs, setJobs] = useState<VideoRenderJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<VideoRenderJob | null>(null);
  const [trends, setTrends] = useState<TrendingTopic[]>([]);
  const [isLoadingTrends, setIsLoadingTrends] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [title, setTitle] = useState("Reels Khách Hàng Review");
  const [aspectRatio, setAspectRatio] = useState<"9:16" | "1:1" | "16:9">("9:16");
  const [duration, setDuration] = useState<number>(15);
  const [hookCaption, setHookCaption] = useState("BÍ QUYẾT GIỮ DA ĐẸP 3 BƯỚC");
  const [captionStyle, setCaptionStyle] = useState<VideoCaptionStyle>("bold_yellow");
  const [normalizeAudio, setNormalizeAudio] = useState(true);

  const workspaceId = getActiveWorkspaceId() || "default-ws";



  const handleApplyTrend = async (trend: TrendingTopic) => {
    setTitle(`${trend.keyword} - TikTok Shorts`);
    setHookCaption(trend.sample_hook);
    setAspectRatio("9:16");
    setDuration(15);
    setCaptionStyle("bold_yellow");
  };

  // Fetch jobs
  const fetchJobs = useCallback(async () => {
    if (!workspaceId) return;
    const res = await listRenderJobs(workspaceId);
    if (res.ok) {
      setJobs(res.data.items);
      setSelectedJob((prev) => {
        if (!prev) return res.data.items[0] ?? null;
        const updated = res.data.items.find((j) => j.id === prev.id);
        if (!updated) return res.data.items[0] ?? null;
        if (
          updated.status === prev.status &&
          updated.progress_percent === prev.progress_percent &&
          updated.output_url === prev.output_url &&
          updated.error_message === prev.error_message
        ) {
          return prev;
        }
        return updated;
      });
    } else {
      setError(res.message);
    }
    setIsLoading(false);
  }, [workspaceId]);

  useEffect(() => {
    let isMounted = true;

    async function loadInitialData() {
      if (!workspaceId) return;
      try {
        const [jobsRes, trendsRes] = await Promise.all([
          listRenderJobs(workspaceId),
          getHotTrends(workspaceId),
        ]);
        if (!isMounted) return;
        if (jobsRes.ok) {
          setJobs(jobsRes.data.items);
          setSelectedJob((prev) => {
            if (!prev) return jobsRes.data.items[0] ?? null;
            const updated = jobsRes.data.items.find((j) => j.id === prev.id);
            return updated ?? jobsRes.data.items[0] ?? null;
          });
        } else {
          setError(jobsRes.message);
        }

        if (trendsRes.ok && Array.isArray(trendsRes.data)) {
          setTrends(trendsRes.data);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Lỗi kết nối");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
          setIsLoadingTrends(false);
        }
      }
    }

    void loadInitialData();

    const interval = setInterval(async () => {
      if (!isMounted || !workspaceId) return;
      const res = await listRenderJobs(workspaceId);
      if (isMounted && res.ok) {
        setJobs(res.data.items);
      }
    }, 4000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [workspaceId]);

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setIsSubmitting(true);
    setError(null);

    const editPlan = {
      target_aspect_ratio: aspectRatio,
      target_duration_seconds: duration,
      cuts: [{ start_ms: 0, end_ms: duration * 1000, zoom_scale: 1.0 }],
      captions: [
        {
          text: hookCaption.trim() || "HOOK 3 GIÂY GIỮ CHÂN",
          start_ms: 0,
          end_ms: Math.min(3000, duration * 1000),
          style: captionStyle,
          position_y: 0.75,
        },
      ],
      audio: {
        normalize_db: normalizeAudio ? -14.0 : 0.0,
        bg_music_volume: 0.15,
      },
    };

    const res = await createRenderJob(workspaceId, {
      title,
      target_aspect_ratio: aspectRatio,
      edit_plan: editPlan,
    });

    setIsSubmitting(false);

    if (res.ok) {
      setSelectedJob(res.data);
      setJobs((prev) => [res.data, ...prev]);
    } else {
      setError(res.message);
    }
  };

  const handleRetry = async (jobId: string) => {
    const res = await retryRenderJob(workspaceId, jobId);
    if (res.ok) {
      fetchJobs();
    }
  };

  const handleCancel = async (jobId: string) => {
    const res = await cancelRenderJob(workspaceId, jobId);
    if (res.ok) {
      fetchJobs();
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "queued":
        return styles.statusQueued;
      case "rendering":
        return styles.statusRendering;
      case "completed":
        return styles.statusCompleted;
      case "failed":
        return styles.statusFailed;
      default:
        return styles.statusCancelled;
    }
  };

  const [isRefreshingTrends, setIsRefreshingTrends] = useState(false);

  const handleRefreshTrends = async () => {
    if (!workspaceId) return;
    setIsRefreshingTrends(true);
    setError(null);
    const res = await refreshHotTrends(workspaceId);
    setIsRefreshingTrends(false);
    if (res.ok) {
      setTrends(res.data);
    } else {
      setError(res.message);
    }
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerInfo}>
          <h1>🎬 Studio Video Tự Động</h1>
          <p>
            Tự động tối ưu video dọc 9:16 (TikTok, Reels, Shorts), tự chèn phụ đề chữ chạy nổi bật và chỉnh âm thanh to rõ, trong trẻo.
          </p>
        </div>
      </header>

      {error ? (
        <div style={{ padding: "12px 16px", borderRadius: "12px", background: "#fef2f2", border: "1px solid #fecaca", color: "#b91c1c", fontSize: "14px" }}>
          ⚠️ {error}
        </div>
      ) : null}

      {/* Mục Trinh Sát Trend Nóng Hổi Hôm Nay (AI Trend Scout - Milestone #8) */}
      <div className={styles.trendScoutCard}>
        <div className={styles.trendScoutHeader}>
          <div className={styles.trendScoutTitle}>
            <span>🔥 Xu Hướng Nóng Hổi Hôm Nay (AI Trend Scout)</span>
          </div>
          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <span style={{ fontSize: "0.8rem", color: "#64748b" }}>
              Tự động quét & tối ưu cho TikTok / YouTube Shorts
            </span>
            <button
              type="button"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "8px",
                border: "1px solid #C7D2FE",
                background: "#EEF2FF",
                color: "#4338CA",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
              disabled={isRefreshingTrends}
              onClick={handleRefreshTrends}
              title="Quét lại các xu hướng mới nhất từ TikTok và YouTube"
            >
              <span
                style={{
                  display: "inline-block",
                  animation: isRefreshingTrends ? "spin 1s linear infinite" : "none",
                }}
              >
                🔄
              </span>
              {isRefreshingTrends ? "Đang quét..." : "Quét xu hướng mới"}
            </button>
          </div>
        </div>

        {isLoadingTrends ? (
          <div style={{ padding: "1rem", textAlign: "center", color: "#64748b", fontSize: "0.85rem" }}>
            Đang trinh sát các chủ đề hot nhất trên mạng xã hội...
          </div>
        ) : (
          <div className={styles.trendList}>
            {(trends || []).map((t) => (
              <div key={t.id} className={styles.trendItem}>
                <div className={styles.trendTop}>
                  <span className={styles.trendKeyword}>{t.keyword}</span>
                  <span className={styles.trendScoreBadge}>⚡ Hot {t.trend_score}%</span>
                </div>
                <div className={styles.trendHook}>
                  <strong>Hook 3s:</strong> &ldquo;{t.sample_hook}&rdquo;
                </div>
                <button
                  type="button"
                  className={styles.trendActionBtn}
                  onClick={() => handleApplyTrend(t)}
                  title="Dùng ý tưởng trend này để tạo video"
                >
                  ⚡ Dựng Video Theo Trend Này
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className={styles.grid}>
        {/* Cột 1: Cấu hình Render Job & Danh sách Hàng Đợi */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Card Form Tạo Job */}
          <div className={styles.card}>
            <h2 className={styles.cardTitle}>⚙️ Tạo Video Render Job Mới</h2>
            <form onSubmit={handleCreateJob}>
              <div className={styles.formGroup}>
                <label htmlFor="video-title">Tiêu đề Video</label>
                <input
                  id="video-title"
                  type="text"
                  className={styles.input}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Nhập tiêu đề video..."
                  required
                />
              </div>

              <div className={styles.formGroup}>
                <label>Tỉ lệ khung hình</label>
                <div className={styles.ratioGrid}>
                  {[
                    { value: "9:16", icon: "📱", label: "9:16 Dọc", sub: "Reels / TikTok / Shorts" },
                    { value: "1:1", icon: "⏹️", label: "1:1 Vuông", sub: "Instagram & FB Feed" },
                    { value: "16:9", icon: "🖥️", label: "16:9 Ngang", sub: "YouTube Chuẩn" },
                  ].map((r) => (
                    <button
                      key={r.value}
                      type="button"
                      className={`${styles.ratioCard} ${aspectRatio === r.value ? styles.ratioCardActive : ""}`}
                      onClick={() => setAspectRatio(r.value as "9:16" | "1:1" | "16:9")}
                    >
                      <span className={styles.ratioIcon}>{r.icon}</span>
                      <span className={styles.ratioLabel}>{r.label}</span>
                      <span className={styles.ratioSub}>{r.sub}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className={styles.formGroup}>
                <label>Thời lượng mong muốn</label>
                <div className={styles.pillGroup}>
                  {[
                    { val: 15, label: "15s (Story / Hook)" },
                    { val: 30, label: "30s (TikTok Chuẩn)" },
                    { val: 60, label: "60s (Chuyên Sâu)" },
                  ].map((d) => (
                    <button
                      key={d.val}
                      type="button"
                      className={`${styles.pillBtn} ${duration === d.val ? styles.pillBtnActive : ""}`}
                      onClick={() => setDuration(d.val)}
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="hook-caption">3s Hook Subtitle (Chữ động giữ chân)</label>
                <input
                  id="hook-caption"
                  type="text"
                  className={styles.input}
                  value={hookCaption}
                  onChange={(e) => setHookCaption(e.target.value)}
                  placeholder="3 BƯỚC HẾT MỤN TRONG 7 NGÀY..."
                />
              </div>

              <div className={styles.formGroup}>
                <label>Phong cách Chữ Subtitle</label>
                <div className={styles.captionStyleGrid}>
                  {[
                    { val: "bold_yellow", label: "🟡 Vàng Nổi Bật" },
                    { val: "clean_white", label: "⚪ Trắng Tinh Tế" },
                    { val: "neon_cyan", label: "🔵 Neon Cyan" },
                    { val: "boxed_black", label: "⬛ Hộp Đen" },
                  ].map((c) => (
                    <button
                      key={c.val}
                      type="button"
                      className={`${styles.captionStyleBtn} ${captionStyle === c.val ? styles.captionStyleBtnActive : ""}`}
                      onClick={() => setCaptionStyle(c.val as VideoCaptionStyle)}
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className={styles.formGroup}>
                <div className={styles.audioNormBox}>
                  <input
                    id="audio-norm"
                    type="checkbox"
                    checked={normalizeAudio}
                    onChange={(e) => setNormalizeAudio(e.target.checked)}
                    className={styles.checkbox}
                  />
                  <label htmlFor="audio-norm" style={{ margin: 0, cursor: "pointer" }}>
                    <strong>Âm thanh chuẩn nghe:</strong> Tự động cân bằng âm lượng to rõ, trong trẻo, không bị nhỏ tiếng hay rè khi xem trên điện thoại.
                  </label>
                </div>
              </div>

              <button
                type="submit"
                className={styles.btnPrimary}
                disabled={isSubmitting}
                style={{ width: "100%", marginTop: "0.5rem" }}
              >
                {isSubmitting ? "Đang xử lý video..." : "🚀 Bắt Đầu Dựng Video Ngay"}
              </button>
            </form>
          </div>

          {/* Card Danh sách Render Jobs */}
          <div className={styles.card}>
            <h2 className={styles.cardTitle}>📋 Hàng Đợi Render ({jobs.length} jobs)</h2>
            {isLoading ? (
              <p style={{ color: "#64748b" }}>Đang tải danh sách jobs...</p>
            ) : jobs.length === 0 ? (
              <div className={styles.emptyState}>
                <p>Chưa có video render job nào.</p>
                <p style={{ fontSize: "0.875rem" }}>Tạo job đầu tiên ở biểu mẫu phía trên để bắt đầu!</p>
              </div>
            ) : (
              <div className={styles.jobsList}>
                {jobs.map((job) => (
                  <div
                    key={job.id}
                    className={`${styles.jobItem} ${selectedJob?.id === job.id ? styles.jobItemActive : ""}`}
                    onClick={() => setSelectedJob(job)}
                    style={{ cursor: "pointer" }}
                  >
                    <div style={{ flex: 1, minWidth: 0, paddingRight: "1rem" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
                        <strong style={{ fontSize: "0.95rem", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {job.title}
                        </strong>
                        <span className={`${styles.statusBadge} ${getStatusBadgeClass(job.status)}`}>
                          {job.status}
                        </span>
                      </div>
                      <div style={{ fontSize: "0.8rem", color: "#64748b" }}>
                        {job.target_aspect_ratio} • Engine: {(job.renderer_engine || "FFMPEG").toUpperCase()} • {new Date(job.created_at).toLocaleTimeString("vi-VN")}
                      </div>

                      {/* Thanh tiến độ nếu đang render */}
                      {job.status === "rendering" && (
                        <div className={styles.progressBarContainer}>
                          <div
                            className={styles.progressBarFill}
                            style={{ width: `${job.progress_percent}%` }}
                          />
                        </div>
                      )}
                    </div>

                    {/* Nút thao tác */}
                    <div style={{ display: "flex", gap: "0.5rem" }} onClick={(e) => e.stopPropagation()}>
                      {job.status === "failed" && (
                        <button
                          className={styles.btnSecondary}
                          onClick={() => handleRetry(job.id)}
                          title="Thử lại render"
                        >
                          🔄 Thử lại
                        </button>
                      )}
                      {(job.status === "queued" || job.status === "rendering") && (
                        <button
                          className={styles.btnSecondary}
                          onClick={() => handleCancel(job.id)}
                          title="Huỷ tác vụ"
                        >
                          ⏹️ Huỷ
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Cột 2: Phone Mockup Canvas & Preview Output */}
        <div className={styles.card}>
          <h2 className={styles.cardTitle}>📱 Bản Xem Trước 9:16</h2>
          <div className={styles.previewCanvas}>
            <div className={styles.phoneFrame}>
              {selectedJob?.output_url ? (
                <video
                  src={selectedJob.output_url}
                  controls
                  autoPlay
                  loop
                  className={styles.videoElement}
                />
              ) : (
                <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b", fontSize: "0.85rem", padding: "1rem", textAlign: "center" }}>
                  {selectedJob?.status === "rendering" ? (
                    <div>
                      <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>⚡</div>
                      <div>Đang render {selectedJob.progress_percent}%...</div>
                    </div>
                  ) : selectedJob?.status === "queued" ? (
                    <div>
                      <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>⏳</div>
                      <div>Đang trong hàng đợi...</div>
                    </div>
                  ) : (
                    <div>Khung hình xem trước 1080x1920</div>
                  )}
                </div>
              )}

              {/* Mô phỏng Kinetic Caption */}
              <div
                className={styles.captionOverlay}
                style={{
                  color:
                    captionStyle === "bold_yellow"
                      ? "#facc15"
                      : captionStyle === "neon_cyan"
                      ? "#22d3ee"
                      : "#ffffff",
                }}
              >
                {hookCaption || "3 GIÂY HOOK GIỮ CHÂN KHÁCH"}
              </div>
            </div>
          </div>

          {selectedJob && (
            <div style={{ marginTop: "1rem", fontSize: "0.875rem", color: "#475569" }}>
              <div style={{ marginBottom: "0.25rem" }}>
                <strong>Job ID:</strong> <code style={{ fontSize: "0.75rem" }}>{selectedJob.id}</code>
              </div>
              <div style={{ marginBottom: "0.25rem" }}>
                <strong>Tiến độ:</strong> {selectedJob.progress_percent}%
              </div>
              {selectedJob.output_url && (
                <div style={{ marginTop: "0.75rem" }}>
                  <a
                    href={selectedJob.output_url}
                    target="_blank"
                    rel="noreferrer"
                    className={styles.btnPrimary}
                    style={{ textDecoration: "none", display: "flex", width: "100%" }}
                  >
                    ⬇️ Tải Video MP4 Đầu Ra
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
