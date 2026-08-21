/**
 * Pro AI 9:16 Short Video Generator (Full-Bleed Visual & CapCut Kinetic Subtitles Engine)
 * Thiết kế chuẩn Viral Short-form Video 2026:
 * - 100% Hình ảnh thật tràn viền sắc nét với chuyển động Cinematic Ken Burns
 * - Phụ đề chữ nổi CapCut ở 1/3 dưới màn hình (Vàng/Trắng viền đen 3D + Emojis)
 * - Hiệu ứng chuyển cảnh mượt mà giữa 3 hình ảnh thật (Hook -> Value -> CTA)
 * - Nhạc nền Web Audio Synth sôi động + Thanh tiến trình thời lượng
 */

export interface KineticVideoOptions {
  text: string;
  channel: string;
  mediaNote?: string | null;
  imageUrl?: string;
  brandName?: string;
  hotline?: string;
  secondaryImages?: string[];
}

export async function generateKineticShortVideo(
  options: KineticVideoOptions,
): Promise<string> {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return "/test_tiktok.mp4";
  }

  const rawText = options.text || "";

  // 1. Phân tích ngữ nghĩa & Tách 3 câu ngắn gọn, cô đọng nhất
  const rawSentences = rawText
    .split(/[.\n!?]/)
    .map((s) => s.replace(/^[•*"-]\s*/, "").trim())
    .filter((s) => s.length >= 4);

  let hookLine = "BÍ QUYẾT TỰ HỌC AI AGENT CHO NGƯỜI MỚI";
  let valueLine = "Nắm chắc quy trình 3 bước làm chủ công nghệ thực chiến";
  let ctaLine = "Ghé trung tâm xem demo & nhận tư vấn 1:1 miễn phí!";

  if (rawSentences.length >= 1) {
    hookLine = rawSentences[0].toUpperCase();
    if (hookLine.length > 60) hookLine = hookLine.slice(0, 57) + "...";
  }
  if (rawSentences.length >= 2) {
    valueLine = rawSentences[1];
    if (valueLine.length > 70) valueLine = valueLine.slice(0, 67) + "...";
  }
  if (rawSentences.length >= 3) {
    ctaLine = rawSentences[rawSentences.length - 1];
    if (ctaLine.length > 65) ctaLine = ctaLine.slice(0, 62) + "...";
  }

  // 2. Tạo Canvas dọc chuẩn 9:16 (540 x 960 px)
  const width = 540;
  const height = 960;
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");

  if (!ctx || !canvas.captureStream || typeof MediaRecorder === "undefined") {
    return "/test_tiktok.mp4";
  }

  // 3. Tải 3 hình ảnh chất lượng cao để làm 3 phân cảnh B-Roll
  const imageSources = [
    options.imageUrl || "https://images.unsplash.com/photo-1531482615713-2afd69097998?w=1200&q=80",
    (options.secondaryImages && options.secondaryImages[0]) ||
      "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=1200&q=80",
    (options.secondaryImages && options.secondaryImages[1]) ||
      "https://images.unsplash.com/photo-1552664730-d307ca884978?w=1200&q=80",
  ];

  const loadedImages: HTMLImageElement[] = [];
  for (let i = 0; i < 3; i++) {
    const img = new Image();
    img.crossOrigin = "anonymous";
    await new Promise<void>((resolve) => {
      img.onload = () => resolve();
      img.onerror = () => resolve();
      img.src = imageSources[i];
    });
    loadedImages.push(img);
  }

  // 4. Khởi tạo âm thanh nhạc nền Lo-Fi Piano du dương, rõ ràng chuẩn Studio
  let audioStreamTrack: MediaStreamTrack | null = null;
  let audioCtx: AudioContext | null = null;
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

      // Bộ lọc âm ấm áp (Lowpass 1200Hz - giữ lại sự trong trẻo của tiếng piano mà không bị chói)
      const filter = audioCtx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.setValueAtTime(1200, audioCtx.currentTime);

      const masterGain = audioCtx.createGain();
      masterGain.gain.setValueAtTime(0.35, audioCtx.currentTime); // Âm lượng rõ ràng, bắt tai
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

      for (let i = 0; i < 20; i++) {
        const noteFreq = notes[i % notes.length];
        const noteTime = audioCtx.currentTime + i * noteInterval;

        const osc = audioCtx.createOscillator();
        const noteGain = audioCtx.createGain();

        // Sử dụng sóng Sine kết hợp hài âm Piano
        osc.type = i % 2 === 0 ? "sine" : "triangle";
        osc.frequency.setValueAtTime(noteFreq, noteTime);

        // Envelope phím piano gảy: Bật nhanh 0.02s và ngân vang tự nhiên
        noteGain.gain.setValueAtTime(0.001, noteTime);
        noteGain.gain.linearRampToValueAtTime(0.4, noteTime + 0.03);
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
  const durationSec = 9; // 9 giây (Scene 1: 0-3s, Scene 2: 3-6s, Scene 3: 6-9s)
  const totalFrames = fps * durationSec;

  const canvasStream = canvas.captureStream(fps);
  const combinedStream = new MediaStream();
  canvasStream.getVideoTracks().forEach((track) => combinedStream.addTrack(track));
  if (audioStreamTrack) {
    combinedStream.addTrack(audioStreamTrack);
  }

  let mimeType = "video/webm";
  if (MediaRecorder.isTypeSupported("video/mp4;codecs=avc1")) {
    mimeType = "video/mp4;codecs=avc1";
  } else if (MediaRecorder.isTypeSupported("video/mp4")) {
    mimeType = "video/mp4";
  } else if (MediaRecorder.isTypeSupported("video/webm;codecs=vp9")) {
    mimeType = "video/webm;codecs=vp9";
  } else if (MediaRecorder.isTypeSupported("video/webm")) {
    mimeType = "video/webm";
  }

  return new Promise<string>((resolve) => {
    let recorder: MediaRecorder;
    try {
      recorder = new MediaRecorder(combinedStream, {
        mimeType: mimeType,
        videoBitsPerSecond: 3800000,
      });
    } catch {
      resolve("/test_tiktok.mp4");
      return;
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
        const blob = new Blob(chunks, { type: mimeType });
        const videoUrl = URL.createObjectURL(blob);
        resolve(videoUrl);
      } else {
        resolve("/test_tiktok.mp4");
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

      // Xác định Scene hiện tại (0: Hook 0-3s, 1: Value 3-6s, 2: CTA 6-9s)
      let sceneIdx = 0;
      let sceneProgress = currentSec / 3;
      if (currentSec >= 6) {
        sceneIdx = 2;
        sceneProgress = (currentSec - 6) / 3;
      } else if (currentSec >= 3) {
        sceneIdx = 1;
        sceneProgress = (currentSec - 3) / 3;
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
        const grad = ctx.createLinearGradient(-width / 2, -height / 2, width / 2, height / 2);
        grad.addColorStop(0, "#0f172a");
        grad.addColorStop(1, "#1e1b4b");
        ctx.fillStyle = grad;
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

      // Badge góc phải: Nhãn thương hiệu
      ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
      ctx.strokeStyle = "rgba(255, 255, 255, 0.3)";
      roundRect(ctx, width - 150, 35, 126, 36, 18);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#FDE047";
      ctx.font = "bold 12px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
      ctx.fillText("⚡ NHẬT MINH", width - 87, 58);
      ctx.restore();

      // ========================================================
      // 4. PHỤ ĐỀ CAPCUT CHỮ NỔI 3D (LOWER-THIRD KINETIC SUBTITLES)
      // ========================================================
      const subY = height - 340;

      ctx.save();
      if (sceneIdx === 0) {
        // SCENE 1: HOOK 3 GIÂY ĐẦU (Chữ Vàng Neon viền đen 3D)
        // Tag nhỏ
        ctx.fillStyle = "#F59E0B";
        ctx.font = "900 13px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("⚡ 3-SECOND VIRAL HOOK", width / 2, subY);

        // Chữ phụ đề to nổi bật phong cách TikTok
        drawStrokeText(
          ctx,
          hookLine,
          width / 2,
          subY + 45,
          width - 50,
          36,
          "#FDE047",
          "#000000",
          "900 25px -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
          3,
        );

        // Tag phụ
        ctx.fillStyle = "#38BDF8";
        ctx.font = "bold 14px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
        ctx.fillText("✨ Cầm tay chỉ việc 1:1 • Thực hành thực tế", width / 2, subY + 160);
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
          "#FFFFFF",
          "#000000",
          "800 23px -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
          3,
        );

        ctx.fillStyle = "#FBBF24";
        ctx.font = "bold 14px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
        ctx.fillText("🎯 Giải pháp độc quyền • Tối ưu chuyển đổi", width / 2, subY + 160);
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
          "800 22px -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
          3,
        );

        // Nút CTA động
        const pulse = 1.0 + Math.sin(frame * 0.2) * 0.04;
        ctx.save();
        ctx.translate(width / 2, subY + 145);
        ctx.scale(pulse, pulse);
        ctx.fillStyle = "#10B981";
        ctx.shadowColor = "rgba(16, 185, 129, 0.8)";
        ctx.shadowBlur = 16;
        roundRect(ctx, -125, -20, 250, 40, 20);
        ctx.fill();
        ctx.shadowBlur = 0;

        ctx.fillStyle = "#FFFFFF";
        ctx.font = "900 14px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
        ctx.fillText("👉 NHẮN TIN / GỌI NGAY", 0, 5);
        ctx.restore();
      }
      ctx.restore();

      // ========================================================
      // 5. SOUNDWAVE & FOOTER BRANDING (DƯỚI CÙNG)
      // ========================================================
      ctx.save();
      const waveY = height - 100;
      const numBars = 22;
      const barW = 5;
      const barGap = 6;
      const totalWaveW = numBars * (barW + barGap);
      const waveStartX = (width - totalWaveW) / 2;

      for (let i = 0; i < numBars; i++) {
        const barH = 10 + Math.sin(frame * 0.35 + i * 0.6) * 18 + Math.sin(i * 1.5) * 6;
        ctx.fillStyle =
          sceneIdx === 0 ? "#F59E0B" : sceneIdx === 1 ? "#38BDF8" : "#10B981";
        roundRect(ctx, waveStartX + i * (barW + barGap), waveY - barH / 2, barW, barH, 2.5);
        ctx.fill();
      }
      ctx.restore();

      // Hotline & Thương hiệu
      ctx.save();
      ctx.fillStyle = "#F8FAFC";
      ctx.font = "bold 13px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(`${brand} • 📞 ${hotline}`, width / 2, height - 55);
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
