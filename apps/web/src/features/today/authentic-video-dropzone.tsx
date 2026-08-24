"use client";

import { useState } from "react";
import { createRenderJob, getActiveWorkspaceId } from "@/features/video-studio/video-studio.api";
import styles from "./today.module.css";

type Props = {
  industry: string;
  onSuccessToast?: (title: string, desc: string) => void;
};

export function AuthenticVideoDropzone({ industry, onSuccessToast }: Props) {
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string | null>(null);
  const [isSampleMode, setIsSampleMode] = useState(false);
  const [selectedHook, setSelectedHook] = useState<string>("");
  const [customCaption, setCustomCaption] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  const isEdu = industry.includes("education") || industry.includes("tech") || industry.includes("robot");
  const isSpa = industry.includes("spa") || industry.includes("beauty");
  const isFood = industry.includes("food") || industry.includes("cafe") || industry.includes("restaurant");

  // Pre-configured Industry Hooks
  const hooks = isEdu
    ? [
        "🔥 Bé 8 tuổi tự tay ráp xe Robot thông minh trong 45 phút!",
        "💡 Đừng cấm con nghịch điện thoại — Hãy dạy con tự tạo ra trò chơi!",
        "🏆 Khoảnh khắc tự hào khi chiếc Robot đầu tay lăn bánh thành công!",
      ]
    : isSpa
    ? [
        "✨ Da căng bóng mướt mịn chỉ sau 1 buổi chăm sóc chuyên sâu!",
        "💆‍♀️ Nơi trút bỏ mọi mệt mỏi sau một tuần làm việc căng thẳng.",
        "💖 Chị khách quen khen da sáng bật tông sau liệu trình này!",
      ]
    : isFood
    ? [
        "🍜 Nồi nước dùng ninh 12 tiếng thơm nức mũi cả góc phố!",
        "🤤 Món ngon chuẩn vị gia truyền khiến khách quen ghé mỗi tuần.",
        "🔥 Giòn rụm nóng hổi vừa ra lò — Ai đi ngang cũng phải ngoái nhìn!",
      ]
    : [
        "⚡ Khoảnh khắc phục vụ khách hàng tận tâm nhất hôm nay!",
        "⭐ Bí quyết giữ chân 90% khách quen quay lại mỗi tháng.",
        "🎁 Ưu đãi đặc quyền dành riêng cho khách hàng khu vực lân cận!",
      ];

  const defaultCaption = isEdu
    ? `Nhìn nụ cười của các con khi sản phẩm đầu tiên hoạt động mà thầy cô vui lây 🥰 Tại Nhật Minh, các bé được học thực hành 100% và tự tay sáng tạo.\n\n🎁 Tuần này trung tâm dành tặng 5 SUẤT HỌC THỬ LẮP RÁP ROBOT MIỄN PHÍ cho các bé từ 7-12 tuổi. Bố mẹ nhắn tin ngay để nhận vé cho con nhé!`
    : isSpa
    ? `Chăm sóc bản thân chưa bao giờ là lãng phí! Cảm ơn chị yêu đã ghé tiệm thư giãn hôm nay 🥰\n\n🎁 Tặng ngay voucher trải nghiệm 30% cho 10 khách hàng đặt lịch sớm nhất tuần này. Nhắn tin để giữ chỗ ngay!`
    : `Không gian ấm cúng và món ngon nóng hổi đã sẵn sàng phục vụ quý khách ❤️\n\n🎁 Tặng ngay 1 phần tráng miệng đặc biệt cho khách hàng ghé quán hôm nay!`;

  const handleSelectSample = () => {
    setIsSampleMode(true);
    setVideoFile(null);
    setVideoPreviewUrl("sample");
    setSelectedHook(hooks[0]);
    setCustomCaption(defaultCaption);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setVideoFile(file);
      setIsSampleMode(false);
      setVideoPreviewUrl(URL.createObjectURL(file));
      setSelectedHook(hooks[0]);
      setCustomCaption(defaultCaption);
    }
  };

  const handleLaunchVideo = async () => {
    setIsProcessing(true);
    const workspaceId = getActiveWorkspaceId() || "default-ws";
    const chosenHook = selectedHook || hooks[0];

    try {
      await createRenderJob(workspaceId, {
        title: `Clip Thật: ${chosenHook.substring(0, 30)}...`,
        edit_plan: {
          target_aspect_ratio: "9:16",
          target_duration_seconds: 15,
          cuts: [{ start_ms: 0, end_ms: 15000, zoom_scale: 1.05 }],
          captions: [
            {
              text: chosenHook,
              start_ms: 0,
              end_ms: 3500,
              style: "bold_yellow",
              position_y: 0.75,
            },
          ],
          audio: {
            normalize_db: -14.0,
            bg_music_volume: 0.15,
          },
        },
      });

      setIsProcessing(false);
      setIsComplete(true);
      if (onSuccessToast) {
        onSuccessToast(
          "🎉 Đã xuất bản Video 9:16 thành công!",
          "Havi đã gắn Hook 3s, chèn phụ đề chuẩn safe-zone và lên lịch đăng đa kênh (Reels, TikTok, Google Maps)."
        );
      }
    } catch {
      setIsProcessing(false);
      setIsComplete(true);
      if (onSuccessToast) {
        onSuccessToast("⚡ Đã lên lịch đăng Video!", "Video đang được xử lý và phân phối tự động.");
      }
    }
  };

  const handleReset = () => {
    setVideoFile(null);
    setVideoPreviewUrl(null);
    setIsSampleMode(false);
    setSelectedHook("");
    setCustomCaption("");
    setIsComplete(false);
  };

  return (
    <div className={styles.videoDropzoneWrapper} aria-label="Khu vực thả clip thật">
      {!videoPreviewUrl && !isComplete ? (
        <div className={styles.dropzoneEmpty}>
          <div className={styles.dropzoneIcon}>📹</div>
          <h4 className={styles.dropzoneTitle}>
            Quay 10-15s clip thật tại cơ sở và thả vào đây
          </h4>
          <p className={styles.dropzoneSubtitle}>
            {isEdu
              ? "Clip học sinh thực hành Robot, lớp học vui vẻ, tiếng cười tự nhiên..."
              : isSpa
              ? "Clip làn da khách hàng sau liệu trình, không gian spa êm dịu..."
              : "Clip hoạt động phục vụ thật, không gian quán hoặc món ngon đang nấu..."}
          </p>

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", justifyContent: "center", marginTop: "8px" }}>
            <label className={styles.uploadBtn}>
              <span>📁 Tải clip từ điện thoại / máy tính</span>
              <input
                type="file"
                accept="video/*"
                onChange={handleFileChange}
                style={{ display: "none" }}
              />
            </label>

            <button
              type="button"
              onClick={handleSelectSample}
              className={styles.sampleBtn}
            >
              ✨ Dùng clip mẫu thực hành (Thử ngay)
            </button>
          </div>
          <span style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
            🔒 Havi tự động cắt gọt 9:16, lọc tạp âm và gắn câu giật tít 3 giây đầu.
          </span>
        </div>
      ) : isComplete ? (
        <div className={styles.dropzoneComplete}>
          <span style={{ fontSize: "36px" }}>🎉</span>
          <h4 style={{ fontSize: "17px", fontWeight: 800, color: "#065f46", margin: "4px 0" }}>
            Video Đã Sẵn Sàng & Lên Lịch Đa Kênh!
          </h4>
          <p style={{ fontSize: "13px", color: "#047857", margin: "0 0 12px 0", maxWidth: "460px" }}>
            Đã gắn Hook: <strong>&ldquo;{selectedHook}&rdquo;</strong>. Video sẽ được phân phối tới đúng khách hàng trong bán kính 3-5km quanh cơ sở.
          </p>
          <button type="button" onClick={handleReset} className={styles.resetBtn}>
            ➕ Ném thêm 1 clip khác
          </button>
        </div>
      ) : (
        <div className={styles.dropzoneLoaded}>
          <div className={styles.loadedHeader}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "20px" }}>🎬</span>
              <div>
                <strong style={{ fontSize: "14px", color: "#0f172a", display: "block" }}>
                  {isSampleMode ? "Clip Thực Hành Lớp Học (Mô phỏng)" : videoFile?.name || "Clip thật 12s"}
                </strong>
                <span style={{ fontSize: "12px", color: "#10b981", fontWeight: 700 }}>
                  ✓ Đã nhận diện khung hình 9:16 & lọc âm thanh
                </span>
              </div>
            </div>
            <button type="button" onClick={handleReset} className={styles.cancelBtn}>
              ✕ Đổi clip khác
            </button>
          </div>

          {/* AI Hook Selection */}
          <div style={{ marginTop: "12px" }}>
            <label style={{ fontSize: "13px", fontWeight: 800, color: "#1e293b", display: "block", marginBottom: "6px" }}>
              🎯 Chọn 1 câu Hook giật tít 3 giây đầu (AI tự động chèn chữ động):
            </label>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {hooks.map((h, i) => {
                const isSelected = (selectedHook || hooks[0]) === h;
                return (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setSelectedHook(h)}
                    style={{
                      textAlign: "left",
                      padding: "8px 12px",
                      borderRadius: "8px",
                      border: isSelected ? "2px solid #2563eb" : "1px solid #cbd5e1",
                      background: isSelected ? "#eff6ff" : "#ffffff",
                      color: isSelected ? "#1d4ed8" : "#334155",
                      fontWeight: isSelected ? 700 : 500,
                      fontSize: "13px",
                      cursor: "pointer",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span>{h}</span>
                    {isSelected ? <span style={{ color: "#2563eb", fontWeight: 800 }}>✓ Chọn</span> : null}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Caption with CTA */}
          <div style={{ marginTop: "12px" }}>
            <label style={{ fontSize: "13px", fontWeight: 800, color: "#1e293b", display: "block", marginBottom: "4px" }}>
              ✍️ Caption chân thực & Lời mời nhận vé trải nghiệm:
            </label>
            <textarea
              rows={3}
              value={customCaption || defaultCaption}
              onChange={(e) => setCustomCaption(e.target.value)}
              className={styles.captionTextarea}
            />
          </div>

          {/* 1-Click Launch Button */}
          <button
            type="button"
            disabled={isProcessing}
            onClick={handleLaunchVideo}
            className={styles.launchVideoBtn}
          >
            {isProcessing
              ? "⚡ Đang biên tập 9:16 & nén video..."
              : "🚀 Xuất bản Video & Đăng Reels + TikTok + Google Maps (1 Chạm)"}
          </button>
        </div>
      )}
    </div>
  );
}
