/**
 * Dynamic Kinetic 9:16 Short Video Generator (Client-Side Canvas Engine)
 * Tự động biến Kịch bản Hook 3s + Ảnh đề tài thành Video dọc 9:16 bắt trend
 * chuẩn Stanford HCI & TikTok/Shorts Retention Heuristics.
 */

export interface KineticVideoOptions {
  text: string;
  channel: string;
  mediaNote?: string | null;
  imageUrl?: string;
  brandName?: string;
  hotline?: string;
}

export async function generateKineticShortVideo(
  options: KineticVideoOptions,
): Promise<string> {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return "/test_tiktok.mp4";
  }

  // 1. Trích xuất & Tinh chỉnh Hook 3s cực kỳ sắc bén, bắt mắt
  let hookTitle = "3 BƯỚC TỰ TẠO AI AGENT CHO RIÊNG BẠN";
  const rawText = options.text || "";

  // Bóc tách nội dung thật, loại bỏ các tiền tố dài dòng
  let cleanedText = rawText
    .replace(/trung tâm công nghệ nhật minh/gi, "")
    .replace(/chia sẻ kỹ thuật thực tế:?/gi, "")
    .replace(/thông báo quan trọng:?/gi, "")
    .replace(/trân trọng giới thiệu:?/gi, "")
    .replace(/tiệm vừa có dịch vụ mới/gi, "giải pháp AI mới")
    .replace(/^[^:]*:\s*/, "")
    .replace(/[•*"-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  const quoteMatch = rawText.match(/["“]([^"”\n]{6,60})["”]/);
  if (quoteMatch && quoteMatch[1]) {
    hookTitle = quoteMatch[1].trim().toUpperCase();
  } else if (cleanedText.length >= 10) {
    const firstSent = cleanedText.split(/[.!?\n]/)[0].trim();
    if (firstSent.length >= 8 && firstSent.length <= 50) {
      hookTitle = firstSent.toUpperCase();
    } else if (rawText.toLowerCase().includes("agent") || rawText.toLowerCase().includes("ai")) {
      hookTitle = "BÍ QUYẾT TỰ HỌC AI AGENT TỪ A-Z";
    } else {
      hookTitle = "ĐỘT PHÁ NĂNG SUẤT VỚI CÔNG NGHỆ AI MỚI";
    }
  }

  // Tạo canvas 9:16 dọc chuẩn 540x960
  const width = 540;
  const height = 960;
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");

  if (!ctx || !canvas.captureStream || typeof MediaRecorder === "undefined") {
    return "/test_tiktok.mp4";
  }

  // Tải hình ảnh nền
  const bgImg = new Image();
  bgImg.crossOrigin = "anonymous";
  const imgUrl =
    options.imageUrl ||
    "https://images.unsplash.com/photo-1531482615713-2afd69097998?w=1200&q=80";

  await new Promise<void>((resolve) => {
    bgImg.onload = () => resolve();
    bgImg.onerror = () => resolve();
    bgImg.src = imgUrl;
  });

  const fps = 30;
  const durationSec = 6;
  const totalFrames = fps * durationSec; // 6 giây hoàn chỉnh
  const stream = canvas.captureStream(fps);

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
      recorder = new MediaRecorder(stream, {
        mimeType: mimeType,
        videoBitsPerSecond: 3000000,
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
      if (chunks.length > 0) {
        const blob = new Blob(chunks, { type: mimeType });
        const videoUrl = URL.createObjectURL(blob);
        resolve(videoUrl);
      } else {
        resolve("/test_tiktok.mp4");
      }
    };

    // Khởi chạy ghi hình
    recorder.start(100);

    let frame = 0;
    const channelLabel =
      options.channel === "tiktok"
        ? "🔥 TIKTOK TRENDING"
        : options.channel === "youtube"
        ? "🎬 YOUTUBE SHORTS"
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

      const progress = frame / totalFrames;

      // 1. Nền chuyển động Ken Burns zoom mượt
      ctx!.save();
      const scale = 1.0 + progress * 0.08;
      ctx!.translate(width / 2, height / 2);
      ctx!.scale(scale, scale);
      if (bgImg.complete && bgImg.naturalWidth > 0) {
        const imgAspect = bgImg.naturalWidth / bgImg.naturalHeight;
        const canvasAspect = width / height;
        let drawW = width;
        let drawH = height;
        if (imgAspect > canvasAspect) {
          drawW = height * imgAspect;
        } else {
          drawH = width / imgAspect;
        }
        ctx!.drawImage(bgImg, -drawW / 2, -drawH / 2, drawW, drawH);
      } else {
        const grad = ctx!.createLinearGradient(-width / 2, -height / 2, width / 2, height / 2);
        grad.addColorStop(0, "#0f172a");
        grad.addColorStop(0.5, "#1e1b4b");
        grad.addColorStop(1, "#312e81");
        ctx!.fillStyle = grad;
        ctx!.fillRect(-width / 2, -height / 2, width, height);
      }
      ctx!.restore();

      // 2. Lớp phủ Dark Vignette sang trọng
      const overlay = ctx!.createLinearGradient(0, 0, 0, height);
      overlay.addColorStop(0, "rgba(15, 23, 42, 0.85)");
      overlay.addColorStop(0.3, "rgba(15, 23, 42, 0.55)");
      overlay.addColorStop(0.7, "rgba(15, 23, 42, 0.70)");
      overlay.addColorStop(1, "rgba(15, 23, 42, 0.95)");
      ctx!.fillStyle = overlay;
      ctx!.fillRect(0, 0, width, height);

      // 3. Top Channel Badge
      ctx!.save();
      ctx!.fillStyle = "rgba(0, 0, 0, 0.6)";
      ctx!.strokeStyle = "#38BDF8";
      ctx!.lineWidth = 2;
      roundRect(ctx!, width / 2 - 120, 50, 240, 42, 21);
      ctx!.fill();
      ctx!.stroke();

      ctx!.fillStyle = "#38BDF8";
      ctx!.font = "bold 15px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
      ctx!.textAlign = "center";
      ctx!.fillText(channelLabel, width / 2, 77);
      ctx!.restore();

      // 4. Center: Hero Hook Card (Glassmorphic)
      ctx!.save();
      const hookBoxY = 270;
      const hookBoxW = width - 56;
      const hookBoxH = 290;

      // Hộp đen mờ viền vàng neon
      ctx!.shadowColor = "rgba(251, 191, 36, 0.6)";
      ctx!.shadowBlur = 24;
      ctx!.fillStyle = "rgba(15, 23, 42, 0.88)";
      ctx!.strokeStyle = "#F59E0B";
      ctx!.lineWidth = 3;
      roundRect(ctx!, 28, hookBoxY, hookBoxW, hookBoxH, 24);
      ctx!.fill();
      ctx!.stroke();
      ctx!.shadowBlur = 0;

      // Tag nhỏ màu vàng
      ctx!.fillStyle = "#F59E0B";
      ctx!.font = "800 13px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
      ctx!.textAlign = "center";
      ctx!.fillText("⚡ 3-SECOND VIRAL HOOK", width / 2, hookBoxY + 40);

      // Tiêu đề Hook vàng / trắng to rõ
      ctx!.fillStyle = "#FFFFFF";
      ctx!.font = "900 24px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
      wrapText(ctx!, hookTitle, width / 2, hookBoxY + 86, hookBoxW - 44, 34);

      // 2 Tag nổi bật bên dưới
      ctx!.fillStyle = "#10B981";
      ctx!.font = "bold 14px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
      ctx!.fillText("✨ Cầm tay chỉ việc 1:1 • Thực hành dự án thật", width / 2, hookBoxY + hookBoxH - 32);
      ctx!.restore();

      // 5. Soundwave Visualizer (Equalizer)
      ctx!.save();
      const waveY = height - 200;
      const numBars = 18;
      const barW = 6;
      const barGap = 6;
      const totalWaveW = numBars * (barW + barGap);
      const waveStartX = (width - totalWaveW) / 2;

      for (let i = 0; i < numBars; i++) {
        const barH = 12 + Math.sin(frame * 0.25 + i * 0.45) * 22 + Math.random() * 6;
        ctx!.fillStyle = i % 2 === 0 ? "#F59E0B" : "#38BDF8";
        roundRect(
          ctx!,
          waveStartX + i * (barW + barGap),
          waveY - barH / 2,
          barW,
          barH,
          3,
        );
        ctx!.fill();
      }
      ctx!.restore();

      // 6. Brand Footer
      ctx!.save();
      ctx!.fillStyle = "#F8FAFC";
      ctx!.font = "bold 16px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
      ctx!.textAlign = "center";
      ctx!.fillText(brand, width / 2, height - 110);

      ctx!.fillStyle = "#FDE047";
      ctx!.font = "800 15px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
      ctx!.fillText(`📞 Hotline: ${hotline} • #Shorts #xuhuong`, width / 2, height - 80);
      ctx!.restore();

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

function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number,
) {
  const words = text.split(" ");
  let line = "";
  let curY = y;

  for (let n = 0; n < words.length; n++) {
    const testLine = line + words[n] + " ";
    const metrics = ctx.measureText(testLine);
    const testWidth = metrics.width;
    if (testWidth > maxWidth && n > 0) {
      ctx.fillText(line.trim(), x, curY);
      line = words[n] + " ";
      curY += lineHeight;
      if (curY > y + lineHeight * 3) {
        ctx.fillText("...", x, curY);
        return;
      }
    } else {
      line = testLine;
    }
  }
  ctx.fillText(line.trim(), x, curY);
}
