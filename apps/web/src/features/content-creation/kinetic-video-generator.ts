/**
 * Pro AI 9:16 Short Video Generator (Full-Bleed Visual & CapCut Kinetic Subtitles Engine)
 * Thiết kế chuẩn Viral Short-form Video 2026:
 * - 100% Hình ảnh thật tràn viền sắc nét với chuyển động Cinematic Ken Burns
 * - Phụ đề chữ nổi CapCut ở 1/3 dưới màn hình (Vàng/Trắng viền đen 3D + Emojis)
 * - Hiệu ứng chuyển cảnh mượt mà giữa 3 hình ảnh thật (Hook -> Value -> CTA)
 * - Nhạc nền Web Audio Synth sôi động + Thanh tiến trình thời lượng
 */

import { readTokens } from "@/lib/auth/token-store";

export type VideoStylePreset = "capcut_pop" | "authentic_story" | "flash_sale";
export type VideoVoiceChoice = "vi-VN-HoaiMyNeural" | "vi-VN-NamMinhNeural";

export interface KineticVideoOptions {
  text: string;
  channel: string;
  mediaNote?: string | null;
  imageUrl?: string;
  brandName?: string;
  hotline?: string;
  secondaryImages?: string[];
  stylePreset?: VideoStylePreset;
  voiceChoice?: VideoVoiceChoice;
}

export async function generateKineticShortVideo(
  options: KineticVideoOptions,
): Promise<string> {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return "/test_tiktok.mp4";
  }

  const rawText = options.text || "";

  // 1. Phân tích ngữ nghĩa động từ đúng bài viết của người dùng
  const rawSentences = rawText
    .split(/[\n.!?]+/)
    .map((s) => s.replace(/^[•*"-]\s*/, "").trim())
    .filter((s) => s.length >= 5 && !s.startsWith("#"));

  let hookLine = rawText.slice(0, 60);
  let valueLine = rawText.slice(60, 140) || rawText.slice(0, 60);
  let ctaLine = "Nhắn tin hoặc ghé tiệm ngay hôm nay để nhận tư vấn!";

  if (rawSentences.length >= 1) {
    hookLine = rawSentences[0].toUpperCase();
    if (hookLine.length > 65) hookLine = hookLine.slice(0, 62) + "...";
  }
  if (rawSentences.length >= 2) {
    valueLine = rawSentences[1];
    if (valueLine.length > 75) valueLine = valueLine.slice(0, 72) + "...";
  }
  if (rawSentences.length >= 3) {
    const last = rawSentences[rawSentences.length - 1];
    if (last.length > 8) {
      ctaLine = last;
      if (ctaLine.length > 70) ctaLine = ctaLine.slice(0, 67) + "...";
    }
  }

  // 2. Render bản cuối 1080 × 1920. Toàn bộ layout bên dưới vẫn dùng hệ
  // tọa độ logic 540 × 960 rồi scale 2x để giữ đúng tỷ lệ, font và animation.
  const width = 540;
  const height = 960;
  const canvas = document.createElement("canvas");
  canvas.width = width * 2;
  canvas.height = height * 2;
  const ctx = canvas.getContext("2d");

  if (!ctx || !canvas.captureStream || typeof MediaRecorder === "undefined") {
    return "/test_tiktok.mp4";
  }
  ctx.scale(2, 2);

  // 3. Tải hình ảnh thật của tiệm hoặc thư viện hình ảnh thực tế chuẩn ngành nghề
  const userImg = options.imageUrl || "";
  let imageSources: string[] = [];

  if (userImg) {
    imageSources = [
      userImg,
      (options.secondaryImages && options.secondaryImages[0]) || userImg,
      (options.secondaryImages && options.secondaryImages[1]) || (options.secondaryImages && options.secondaryImages[0]) || userImg,
    ];
  } else {
    // Tự động nhận diện ngành nghề để lấy bộ ảnh thực tế độ phân giải cao 9:16
    const lower = (rawText + " " + (options.brandName || "")).toLowerCase();
    if (lower.includes("spa") || lower.includes("dưỡng sinh") || lower.includes("massage") || lower.includes("da") || lower.includes("chăm sóc")) {
      imageSources = ["/images/spa_photo_hq.jpg", "/ai-samples/facial_care.jpg", "/ai-samples/herbal_wash.jpg"];
    } else if (lower.includes("cà phê") || lower.includes("cafe") || lower.includes("trà") || lower.includes("quán") || lower.includes("ẩm thực")) {
      imageSources = ["/images/cafe_photo_hq.jpg", "/images/cafe_photo.jpg", "/images/cafe_photo_hq.jpg"];
    } else if (lower.includes("bất động sản") || lower.includes("nhà") || lower.includes("đất") || lower.includes("căn hộ")) {
      imageSources = ["/images/bds_photo_hq.jpg", "/images/bds_photo.jpg", "/images/bds_photo_hq.jpg"];
    } else {
      // Mặc định: Ngành Công nghệ / Laptop / Điện tử / Kỹ thuật Nhật Minh
      imageSources = ["/images/hero_ai_studio_hq.jpg", "/images/hero_photo.jpg", "/images/hero_ai_studio_hq.jpg"];
    }
  }

  const loadedImages: HTMLImageElement[] = [];
  for (const src of imageSources) {
    if (!src) continue;
    try {
      const img = new Image();
      if (!src.startsWith("blob:") && !src.startsWith("data:")) {
        img.crossOrigin = "anonymous";
      }
      await new Promise<void>((resolve) => {
        img.onload = () => {
          loadedImages.push(img);
          resolve();
        };
        img.onerror = () => {
          // Thử lại không có crossOrigin nếu gặp sự cố CORS
          const retryImg = new Image();
          retryImg.onload = () => {
            loadedImages.push(retryImg);
            resolve();
          };
          retryImg.onerror = () => resolve();
          retryImg.src = src;
        };
        img.src = src;
      });
    } catch {
      // fallback
    }
  }

  // 4. Khởi tạo âm thanh: Giọng đọc AI Tiếng Việt (Edge-TTS 0đ) + Nhạc nền Lo-Fi Piano du dương
  let audioStreamTrack: MediaStreamTrack | null = null;
  let audioCtx: AudioContext | null = null;
  let voiceBuffer: AudioBuffer | null = null;

  try {
    const AudioContextClass =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
      if (audioCtx.state === "suspended") {
        await audioCtx.resume();
      }

      const dest = audioCtx.createMediaStreamDestination();

      // 4.1 Tải giọng đọc AI Tiếng Việt từ /voice/tts
      try {
        const tokens = readTokens();
        const apiBase =
          process.env.NEXT_PUBLIC_API_BASE_URL ??
          (typeof window !== "undefined" && window.location.port !== "3000"
            ? window.location.origin
            : "http://localhost:8000");
        const ttsText = `${hookLine}. ${valueLine}. ${ctaLine}`;
        const ttsRes = await fetch(`${apiBase}/voice/tts`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(tokens?.accessToken ? { Authorization: `Bearer ${tokens.accessToken}` } : {}),
            ...(tokens?.activeWorkspaceId ? { "X-Workspace-Id": tokens.activeWorkspaceId } : {}),
          },
          body: JSON.stringify({
            text: ttsText,
            voice: options.voiceChoice || "vi-VN-HoaiMyNeural",
            rate: "+10%",
          }),
        });
        if (ttsRes.ok) {
          const arrayBuf = await ttsRes.arrayBuffer();
          voiceBuffer = await audioCtx.decodeAudioData(arrayBuf);
        }
      } catch {
        // Fallback âm thanh nhẹ nhàng nếu offline / test environment
      }

      // Nếu có giọng đọc AI, lồng vào stream âm thanh
      if (voiceBuffer) {
        const voiceSource = audioCtx.createBufferSource();
        voiceSource.buffer = voiceBuffer;
        const voiceGain = audioCtx.createGain();
        voiceGain.gain.setValueAtTime(1.0, audioCtx.currentTime);
        voiceSource.connect(voiceGain);
        voiceGain.connect(dest);
        voiceSource.start(audioCtx.currentTime + 0.3); // Bắt đầu đọc sau 0.3s
      }

      // 4.2 Nhạc nền Lo-Fi Piano bắt tai (hạ âm lượng nếu có giọng đọc AI để giọng luôn trong trẻo)
      const filter = audioCtx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.setValueAtTime(1200, audioCtx.currentTime);

      const masterGain = audioCtx.createGain();
      masterGain.gain.setValueAtTime(voiceBuffer ? 0.15 : 0.35, audioCtx.currentTime);
      filter.connect(masterGain);
      masterGain.connect(dest);

      // Chuỗi giai điệu Lo-Fi Piano bắt tai (C Major Pentatonic Pop Chimes)
      const notes = [
        261.63, // C4
        329.63, // E4
        392.00, // G4
        523.25, // C5
        440.00, // A4
        392.00, // G4
        329.63, // E4
        293.66, // D4
      ];
      const noteInterval = 0.5; // Mỗi nốt 0.5 giây
      const actualVoiceSec = voiceBuffer ? voiceBuffer.duration : 9;
      const totalNotesNeeded = Math.ceil((actualVoiceSec + 3) / noteInterval);

      for (let i = 0; i < totalNotesNeeded; i++) {
        const noteFreq = notes[i % notes.length];
        const noteTime = audioCtx.currentTime + i * noteInterval;

        const osc = audioCtx.createOscillator();
        const noteGain = audioCtx.createGain();

        osc.type = i % 2 === 0 ? "sine" : "triangle";
        osc.frequency.setValueAtTime(noteFreq, noteTime);

        noteGain.gain.setValueAtTime(0.001, noteTime);
        noteGain.gain.linearRampToValueAtTime(0.3, noteTime + 0.03);
        noteGain.gain.exponentialRampToValueAtTime(0.001, noteTime + noteInterval);

        osc.connect(noteGain);
        noteGain.connect(filter);

        osc.start(noteTime);
        osc.stop(noteTime + noteInterval);
      }

      const tracks = dest.stream.getAudioTracks();
      if (tracks.length > 0) {
        audioStreamTrack = tracks[0];
      }
    }
  } catch {
    // Audio context fallback gracefully
  }

  const fps = 30;
  // Tự động co giãn thời lượng video khớp 100% với giọng đọc AI thực tế (+1.5s outro để nhạc du dương)
  const voiceDuration = voiceBuffer ? voiceBuffer.duration : 0;
  const durationSec = voiceDuration > 0 ? Math.max(Math.ceil(voiceDuration + 1.5), 10) : 10;
  const totalFrames = fps * durationSec;

  const canvasStream = canvas.captureStream(fps);
  const combinedStream = new MediaStream();
  canvasStream.getVideoTracks().forEach((track) => combinedStream.addTrack(track));
  if (audioStreamTrack) {
    combinedStream.addTrack(audioStreamTrack);
  }

  // Tìm mimeType mà trình duyệt thực tế hỗ trợ (đặc biệt Safari Mac hỗ trợ video/mp4, Chrome hỗ trợ video/webm)
  const preferredMimeTypes = [
    "video/mp4;codecs=avc1,mp4a.40.2",
    "video/mp4;codecs=avc1",
    "video/mp4",
    "video/webm;codecs=vp9,opus",
    "video/webm;codecs=vp8,opus",
    "video/webm;codecs=h264,opus",
    "video/webm",
  ];

  let selectedMime = "";
  if (typeof MediaRecorder !== "undefined" && typeof MediaRecorder.isTypeSupported === "function") {
    for (const type of preferredMimeTypes) {
      if (MediaRecorder.isTypeSupported(type)) {
        selectedMime = type;
        break;
      }
    }
  }

  return new Promise<string>((resolve, reject) => {
    let recorder: MediaRecorder;
    const actualMime = selectedMime;

    try {
      if (selectedMime) {
        recorder = new MediaRecorder(combinedStream, { mimeType: selectedMime });
      } else {
        recorder = new MediaRecorder(combinedStream);
      }
    } catch {
      try {
        // Fallback: Thử với canvasStream thuần nếu combined audio stream bị Safari từ chối
        if (selectedMime) {
          recorder = new MediaRecorder(canvasStream, { mimeType: selectedMime });
        } else {
          recorder = new MediaRecorder(canvasStream);
        }
      } catch (err) {
        console.error("Không thể khởi tạo MediaRecorder:", err);
        reject(new Error("Trình duyệt không hỗ trợ quay màn hình video trực tiếp."));
        return;
      }
    }

    const chunks: Blob[] = [];
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        chunks.push(e.data);
      }
    };

    recorder.onstop = () => {
      if (audioCtx && audioCtx.state !== "closed") {
        audioCtx.close().catch(() => {});
      }
      if (chunks.length > 0) {
        const finalBlobType = actualMime || chunks[0].type || "video/mp4";
        const blob = new Blob(chunks, { type: finalBlobType });
        const videoUrl = URL.createObjectURL(blob);
        resolve(videoUrl);
      } else {
        reject(new Error("Không thể trích xuất dữ liệu video."));
      }
    };

    recorder.start(100);

    let frame = 0;
    const channelLabel =
      options.channel === "tiktok"
        ? "🔥 TIKTOK VIRAL"
        : options.channel === "youtube"
        ? "🎬 SHORTS TRENDING"
        : "✨ FACEBOOK REELS";

    const brand = options.brandName || "TRUNG TÂM CÔNG NGHỆ NHẬT MINH";
    const hotline = options.hotline || "0984 883 750";

    const intervalId = setInterval(() => {
      if (frame >= totalFrames) {
        clearInterval(intervalId);
        if (recorder.state === "recording") {
          recorder.stop();
        }
        return;
      }

      const currentSec = frame / fps;
      const progress = frame / totalFrames;

      // Xác định Scene hiện tại dựa trên durationSec thực tế
      let sceneIdx = 0;
      let sceneProgress = 0;
      const s1Duration = Math.min(3.5, durationSec * 0.28);
      const s3Duration = Math.min(3.5, durationSec * 0.28);
      const s2Duration = Math.max(durationSec - s1Duration - s3Duration, 3);

      if (currentSec < s1Duration) {
        sceneIdx = 0;
        sceneProgress = currentSec / s1Duration;
      } else if (currentSec < s1Duration + s2Duration) {
        sceneIdx = 1;
        sceneProgress = (currentSec - s1Duration) / s2Duration;
      } else {
        sceneIdx = 2;
        sceneProgress = (currentSec - s1Duration - s2Duration) / s3Duration;
      }

      const currentBgImg = loadedImages[sceneIdx] || loadedImages[0];

      // ========================================================
      // 1. VẼ HÌNH ẢNH THẬT 100% TRÀN VIỀN (CINEMATIC FULL-BLEED)
      // ========================================================
      ctx.save();
      // Chuyển động Zoom chậm (Ken Burns Motion)
      const zoomScale = 1.02 + sceneProgress * 0.1;
      const panX = Math.sin(sceneProgress * Math.PI) * 15;
      const panY = (sceneProgress - 0.5) * 20;
      ctx.translate(width / 2 + panX, height / 2 + panY);
      ctx.scale(zoomScale, zoomScale);

      if (currentBgImg && currentBgImg.complete && currentBgImg.naturalWidth > 0) {
        const imgAspect = currentBgImg.naturalWidth / currentBgImg.naturalHeight;
        const canvasAspect = width / height;
        let drawW = width;
        let drawH = height;
        if (imgAspect > canvasAspect) {
          drawW = height * imgAspect;
        } else {
          drawH = width / imgAspect;
        }
        ctx.drawImage(currentBgImg, -drawW / 2, -drawH / 2, drawW, drawH);
      } else {
        // Nền Motion Graphics Studio cao cấp (gradient đa tầng + quả cầu ánh sáng chuyển động)
        const isFlash = options.stylePreset === "flash_sale";
        const isStory = options.stylePreset === "authentic_story";

        const grad = ctx.createLinearGradient(-width / 2, -height / 2, width / 2, height / 2);
        if (isFlash) {
          grad.addColorStop(0, "#450a0a");
          grad.addColorStop(0.5, "#1c1917");
          grad.addColorStop(1, "#7f1d1d");
        } else if (isStory) {
          grad.addColorStop(0, "#09090b");
          grad.addColorStop(0.5, "#18181b");
          grad.addColorStop(1, "#27272a");
        } else {
          grad.addColorStop(0, "#0f172a");
          grad.addColorStop(0.5, "#1e1b4b");
          grad.addColorStop(1, "#31104b");
        }
        ctx.fillStyle = grad;
        ctx.fillRect(-width / 2, -height / 2, width, height);

        // Vòng sáng hào quang chuyển động
        const orb1X = Math.sin(frame * 0.05) * 120;
        const orb1Y = Math.cos(frame * 0.04) * 160 - 50;
        const orbGrad = ctx.createRadialGradient(orb1X, orb1Y, 10, orb1X, orb1Y, 260);
        orbGrad.addColorStop(0, isFlash ? "rgba(239, 68, 68, 0.45)" : isStory ? "rgba(161, 161, 170, 0.25)" : "rgba(245, 158, 11, 0.35)");
        orbGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = orbGrad;
        ctx.fillRect(-width / 2, -height / 2, width, height);
      }
      ctx.restore();

      // ========================================================
      // 2. LỚP PHỦ GRADIENT NHẸ Ở ĐỈNH VÀ ĐÁY (GIỮ TRỌN 80% ẢNH THẬT)
      // ========================================================
      // Gradient mờ trên đỉnh để tôn Channel Badge
      const topGrad = ctx.createLinearGradient(0, 0, 0, 160);
      topGrad.addColorStop(0, "rgba(0, 0, 0, 0.65)");
      topGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = topGrad;
      ctx.fillRect(0, 0, width, 160);

      // Gradient mờ ở 1/3 dưới để làm nổi bật Phụ đề CapCut
      const bottomGrad = ctx.createLinearGradient(0, height - 420, 0, height);
      bottomGrad.addColorStop(0, "rgba(0, 0, 0, 0)");
      bottomGrad.addColorStop(0.35, "rgba(0, 0, 0, 0.70)");
      bottomGrad.addColorStop(1, "rgba(0, 0, 0, 0.95)");
      ctx.fillStyle = bottomGrad;
      ctx.fillRect(0, height - 420, width, 420);

      // ========================================================
      // 3. TOP BAR: FLOATING BADGES (TIKTOK / SHORTS STYLE)
      // ========================================================
      ctx.save();
      // Badge góc trái
      ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
      ctx.strokeStyle = sceneIdx === 0 ? "#F59E0B" : sceneIdx === 1 ? "#38BDF8" : "#10B981";
      ctx.lineWidth = 2;
      roundRect(ctx, 24, 35, 175, 36, 18);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#FFFFFF";
      ctx.font = "bold 13px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(channelLabel, 111, 58);

      // Badge góc phải: Nhãn thương hiệu động
      const shortBrand = brand.length > 16 ? brand.slice(0, 14) + "..." : brand;
      ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
      ctx.strokeStyle = "rgba(255, 255, 255, 0.3)";
      roundRect(ctx, width - 170, 35, 146, 36, 18);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#FDE047";
      ctx.font = "bold 11px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
      ctx.fillText(`⚡ ${shortBrand}`, width - 97, 58);
      ctx.restore();

      // ========================================================
      // 4. PHỤ ĐỀ CAPCUT CHỮ NỔI 3D (LOWER-THIRD KINETIC SUBTITLES)
      // ========================================================
      const subY = height - 340;

      ctx.save();
      if (sceneIdx === 0) {
        // SCENE 1: HOOK 3 GIÂY ĐẦU (Chữ Vàng Neon viền đen 3D)
        ctx.fillStyle = "#F59E0B";
        ctx.font = "900 13px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("⚡ 3-SECOND VIRAL HOOK", width / 2, subY);

        drawStrokeText(
          ctx,
          hookLine,
          width / 2,
          subY + 45,
          width - 50,
          36,
          options.stylePreset === "flash_sale" ? "#FCA5A5" : options.stylePreset === "authentic_story" ? "#FFFFFF" : "#FDE047",
          "#000000",
          "900 24px -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
          3,
        );

        ctx.fillStyle = "#38BDF8";
        ctx.font = "bold 13px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
        ctx.fillText(`✨ ${brand} • Chia sẻ thực chiến`, width / 2, subY + 160);
      } else if (sceneIdx === 1) {
        // SCENE 2: GIẢI PHÁP / BÍ QUYẾT (Chữ Xanh Cyan nổi bật)
        ctx.fillStyle = "#38BDF8";
        ctx.font = "900 13px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("💡 BÍ QUYẾT & QUY TRÌNH THỰC TẾ", width / 2, subY);

        drawStrokeText(
          ctx,
          valueLine,
          width / 2,
          subY + 45,
          width - 50,
          34,
          options.stylePreset === "flash_sale" ? "#FEE2E2" : "#FFFFFF",
          "#000000",
          "800 22px -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
          3,
        );

        ctx.fillStyle = "#FBBF24";
        ctx.font = "bold 13px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
        ctx.fillText(options.mediaNote ? `📍 ${options.mediaNote.slice(0, 40)}` : "🎯 Quy trình chuẩn • Trải nghiệm thực tế", width / 2, subY + 160);
      } else {
        // SCENE 3: CTA CHỐT LEAD (Nút Xanh Emerald kêu gọi hành động)
        ctx.fillStyle = "#10B981";
        ctx.font = "900 13px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("🚀 NHẬN TƯ VẤN & ƯU ĐÃI NGAY", width / 2, subY);

        drawStrokeText(
          ctx,
          ctaLine,
          width / 2,
          subY + 45,
          width - 50,
          32,
          "#FFFFFF",
          "#000000",
          "800 21px -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
          3,
        );

        // Nút CTA động
        const pulse = 1.0 + Math.sin(frame * 0.2) * 0.04;
        ctx.save();
        ctx.translate(width / 2, subY + 145);
        ctx.scale(pulse, pulse);
        ctx.fillStyle = options.stylePreset === "flash_sale" ? "#EF4444" : "#10B981";
        ctx.shadowColor = options.stylePreset === "flash_sale" ? "rgba(239, 68, 68, 0.8)" : "rgba(16, 185, 129, 0.8)";
        ctx.shadowBlur = 16;
        roundRect(ctx, -135, -20, 270, 40, 20);
        ctx.fill();
        ctx.shadowBlur = 0;

        ctx.fillStyle = "#FFFFFF";
        ctx.font = "900 13px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
        ctx.fillText("👉 NHẮN TIN / LIÊN HỆ NGAY", 0, 5);
        ctx.restore();
      }
      ctx.restore();

      // ========================================================
      // 5. FOOTER BRANDING CARD (DƯỚI CÙNG)
      // ========================================================
      ctx.save();
      ctx.fillStyle = "rgba(0, 0, 0, 0.70)";
      ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
      roundRect(ctx, 30, height - 75, width - 60, 42, 21);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#FFFFFF";
      ctx.font = "bold 13px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(`📍 ${brand} • 📞 ${hotline}`, width / 2, height - 49);
      ctx.restore();

      // ========================================================
      // 6. PROGRESS BAR DƯỚI ĐÁY VIDEO
      // ========================================================
      ctx.save();
      ctx.fillStyle = "rgba(255, 255, 255, 0.2)";
      ctx.fillRect(0, height - 6, width, 6);
      ctx.fillStyle = sceneIdx === 0 ? "#F59E0B" : sceneIdx === 1 ? "#38BDF8" : "#10B981";
      ctx.fillRect(0, height - 6, width * progress, 6);
      ctx.restore();

      frame++;
    }, 1000 / fps);
  });
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

/**
 * Vẽ chữ có viền đen dày 3D (CapCut Stroke Text Style)
 * Đảm bảo chữ luôn sắc nét và đọc rõ 100% trên bất kỳ nền ảnh nào
 */
function drawStrokeText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number,
  fillColor: string,
  strokeColor: string,
  font: string,
  maxLines: number = 3,
) {
  ctx.font = font;
  ctx.textAlign = "center";

  const words = text.split(" ");
  let line = "";
  let curY = y;
  let lineCount = 0;

  for (let n = 0; n < words.length; n++) {
    const testLine = line + words[n] + " ";
    const metrics = ctx.measureText(testLine);
    const testWidth = metrics.width;

    if (testWidth > maxWidth && n > 0) {
      // Stroke viền đen
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 6;
      ctx.lineJoin = "round";
      ctx.miterLimit = 2;
      ctx.strokeText(line.trim(), x, curY);

      // Fill màu chữ
      ctx.fillStyle = fillColor;
      ctx.fillText(line.trim(), x, curY);

      line = words[n] + " ";
      curY += lineHeight;
      lineCount++;

      if (lineCount >= maxLines - 1 && n < words.length - 1) {
        let remaining = "";
        for (let k = n; k < words.length; k++) {
          if (ctx.measureText(remaining + words[k] + "...").width < maxWidth) {
            remaining += words[k] + " ";
          } else {
            break;
          }
        }
        const finalLine = (remaining.trim() || words[n]) + "...";
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = 6;
        ctx.strokeText(finalLine, x, curY);
        ctx.fillStyle = fillColor;
        ctx.fillText(finalLine, x, curY);
        return;
      }
    } else {
      line = testLine;
    }
  }

  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = 6;
  ctx.lineJoin = "round";
  ctx.miterLimit = 2;
  ctx.strokeText(line.trim(), x, curY);
  ctx.fillStyle = fillColor;
  ctx.fillText(line.trim(), x, curY);
}
