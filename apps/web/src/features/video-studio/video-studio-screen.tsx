"use client";

import { useEffect, useState, useRef } from "react";
import {
  listRenderJobs,
  createRenderJob,
  retryRenderJob,
  cancelRenderJob,
  getActiveWorkspaceId,
  getHotTrends,
  synthesizeTrend,
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

  const fetchTrends = async () => {
    if (!workspaceId) return;
    setIsLoadingTrends(true);
    const res = await getHotTrends(workspaceId);
    if (res.ok && Array.isArray(res.data)) {
      setTrends(res.data);
    } else {
      setTrends([]);
    }
    setIsLoadingTrends(false);
  };

  const handleApplyTrend = async (trend: TrendingTopic) => {
    setTitle(`${trend.keyword} - TikTok Shorts`);
    setHookCaption(trend.sample_hook);
    setAspectRatio("9:16");
    setDuration(15);
    setCaptionStyle("bold_yellow");
  };

  // Fetch jobs
  const fetchJobs = async () => {
    if (!workspaceId) return;
    const res = await listRenderJobs(workspaceId);
    if (res.ok) {
      setJobs(res.data.items);
      if (!selectedJob && res.data.items.length > 0) {
        setSelectedJob(res.data.items[0]);
      } else if (selectedJob) {
        const updated = res.data.items.find((j) => j.id === selectedJob.id);
        if (updated) setSelectedJob(updated);
      }
    } else {
      setError(res.message);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchJobs();
    fetchTrends();
    const interval = setInterval(fetchJobs, 4000);
    return () => clearInterval(interval);
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

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerInfo}>
          <h1>🎬 Studio Video & Hàng Đợi Render Độc Lập</h1>
          <p>
            Tự động tối ưu video dọc 9:16 (Reels/TikTok/Shorts), chèn kinetic subtitles và chuẩn hoá âm thanh chuẩn EBU R128 (-14 LUFS).
          </p>
        </div>
      </header>

      {/* Mục Trinh Sát Trend Nóng Hổi Hôm Nay (AI Trend Scout - Milestone #8) */}
      <div className={styles.trendScoutCard}>
        <div className={styles.trendScoutHeader}>
          <div className={styles.trendScoutTitle}>
            <span>🔥 Xu Hướng Nóng Hổi Hôm Nay (AI Trend Scout)</span>
          </div>
          <span style={{ fontSize: "0.8rem", color: "#64748b" }}>
            Tự động quét & tối ưu cho TikTok / YouTube Shorts
          </span>
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
                  <strong>Hook 3s:</strong> "{t.sample_hook}"
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

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div className={styles.formGroup}>
                  <label htmlFor="aspect-ratio">Tỉ lệ khung hình</label>
                  <select
                    id="aspect-ratio"
                    className={styles.select}
                    value={aspectRatio}
                    onChange={(e) => setAspectRatio(e.target.value as "9:16" | "1:1" | "16:9")}
                  >
                    <option value="9:16">9:16 (Dọc - Reels / TikTok / Shorts)</option>
                    <option value="1:1">1:1 (Vuông - Instagram Feed)</option>
                    <option value="16:9">16:9 (Ngang - YouTube Standard)</option>
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="duration-sec">Thời lượng mong muốn (giây)</label>
                  <select
                    id="duration-sec"
                    className={styles.select}
                    value={duration}
                    onChange={(e) => setDuration(Number(e.target.value))}
                  >
                    <option value={15}>15 giây (Story / Hook ngắn)</option>
                    <option value={30}>30 giây (TikTok Tiêu chuẩn)</option>
                    <option value={60}>60 giây (Reels Chuyên sâu)</option>
                  </select>
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

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div className={styles.formGroup}>
                  <label htmlFor="caption-style">Phong cách Chữ</label>
                  <select
                    id="caption-style"
                    className={styles.select}
                    value={captionStyle}
                    onChange={(e) => setCaptionStyle(e.target.value as VideoCaptionStyle)}
                  >
                    <option value="bold_yellow">🟡 Vàng Đậm Nổi Bật (Bold Yellow)</option>
                    <option value="clean_white">⚪ Trắng Tinh Tế (Clean White)</option>
                    <option value="neon_cyan">🔵 Neon Cyan Sôi Động</option>
                    <option value="boxed_black">⬛ Hộp Đen Sang Trọng (Boxed Black)</option>
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="audio-norm">Chuẩn hoá Âm thanh</label>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", height: "100%" }}>
                    <input
                      id="audio-norm"
                      type="checkbox"
                      checked={normalizeAudio}
                      onChange={(e) => setNormalizeAudio(e.target.checked)}
                      style={{ width: "18px", height: "18px", accentColor: "#6366f1" }}
                    />
                    <span style={{ fontSize: "0.875rem", color: "#475569" }}>
                      Chuẩn hoá -14 LUFS (EBU R128)
                    </span>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                className={styles.btnPrimary}
                disabled={isSubmitting}
                style={{ width: "100%", marginTop: "0.5rem" }}
              >
                {isSubmitting ? "Đang xếp hàng..." : "🚀 Bắt đầu Render Video (Queue: havi.video_render)"}
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
                        {job.target_aspect_ratio} • Engine: {job.renderer_engine.toUpperCase()} • {new Date(job.created_at).toLocaleTimeString("vi-VN")}
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
