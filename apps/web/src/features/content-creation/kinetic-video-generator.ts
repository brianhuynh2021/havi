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

  // Trích xuất Hook 3 giây từ văn bản bài viết
  let hookTitle = "⚡ BÍ QUYẾT BẮT TREND AI";
  const rawText = options.text || "";

  // Ưu tiên 1: Lấy nội dung trong dấu ngoặc kép ("..." hoặc “...”)
  const quoteMatch = rawText.match(/["“]([^"”\n]{6,90})["”]/);
  if (quoteMatch && quoteMatch[1]) {
    hookTitle = quoteMatch[1].trim().toUpperCase();
  } else if (rawText.toLowerCase().includes("hook")) {
    const hookLine = rawText
      .split("\n")
      .find((l) => l.toLowerCase().includes("hook"));
    if (hookLine) {
      const cleaned = hookLine
        .replace(/^[^:]*:\s*/, "")
        .replace(/[•*"-]/g, "")
        .trim();
      if (cleaned.length > 5) {
        hookTitle = cleaned.slice(0, 70).toUpperCase();
      }
    }
  } else {
    const firstSentence = rawText.split(/[.!?\n]/)[0];
    if (firstSentence && firstSentence.length > 8) {
      hookTitle = firstSentence.slice(0, 60).trim().toUpperCase();
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
  const totalFrames = fps * 4; // 4 giây loop
  const stream = canvas.captureStream(fps);

  let mimeType = "video/webm";
  if (MediaRecorder.isTypeSupported("video/mp4")) {
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
        videoBitsPerSecond: 2500000,
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

    recorder.start();

    let frame = 0;
    const channelLabel =
      options.channel === "tiktok"
        ? "🔥 TIKTOK TRENDING"
        : options.channel === "youtube"
        ? "🎬 YOUTUBE SHORTS"
        : "✨ FACEBOOK REELS";

    const brand = options.brandName || "TRUNG TÂM CÔNG NGHỆ NHẬT MINH";
    const hotline = options.hotline || "0984 883 750";

    function drawFrame() {
      if (frame >= totalFrames) {
        recorder.stop();
        return;
      }

      const progress = frame / totalFrames;

      // 1. Vẽ nền với hiệu ứng Ken Burns zoom nhẹ nhàng
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
        // Fallback gradient hiện đại
        const grad = ctx!.createLinearGradient(-width / 2, -height / 2, width / 2, height / 2);
        grad.addColorStop(0, "#1e1b4b");
        grad.addColorStop(0.5, "#312e81");
        grad.addColorStop(1, "#4338ca");
        ctx!.fillStyle = grad;
        ctx!.fillRect(-width / 2, -height / 2, width, height);
      }
      ctx!.restore();

      // 2. Lớp phủ Gradient Tối (Dark Vignette Gradient) để nổi bật Text Hook
      const overlay = ctx!.createLinearGradient(0, 0, 0, height);
      overlay.addColorStop(0, "rgba(15, 23, 42, 0.75)");
      overlay.addColorStop(0.3, "rgba(15, 23, 42, 0.45)");
      overlay.addColorStop(0.7, "rgba(15, 23, 42, 0.65)");
      overlay.addColorStop(1, "rgba(15, 23, 42, 0.92)");
      ctx!.fillStyle = overlay;
      ctx!.fillRect(0, 0, width, height);

      // 3. Top Channel Badge
      ctx!.save();
      ctx!.fillStyle = "rgba(255, 255, 255, 0.15)";
      ctx!.strokeStyle = "rgba(255, 255, 255, 0.3)";
      ctx!.lineWidth = 1.5;
      roundRect(ctx!, width / 2 - 110, 40, 220, 36, 18);
      ctx!.fill();
      ctx!.stroke();

      ctx!.fillStyle = "#38BDF8";
      ctx!.font = "bold 14px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
      ctx!.textAlign = "center";
      ctx!.fillText(channelLabel, width / 2, 63);
      ctx!.restore();

      // 4. Center: Viral Hook Box (Kinetic Typography)
      ctx!.save();
      const hookBoxY = 280;
      const hookBoxW = width - 48;
      const hookBoxH = 260;

      // Glow viền vàng neon bắt mắt
      ctx!.shadowColor = "rgba(251, 191, 36, 0.5)";
      ctx!.shadowBlur = 20;
      ctx!.fillStyle = "rgba(0, 0, 0, 0.75)";
      ctx!.strokeStyle = "#F59E0B";
      ctx!.lineWidth = 3;
      roundRect(ctx!, 24, hookBoxY, hookBoxW, hookBoxH, 20);
      ctx!.fill();
      ctx!.stroke();
      ctx!.shadowBlur = 0;

      // Nhãn Hook trên đầu hộp
      ctx!.fillStyle = "#F59E0B";
      ctx!.font = "800 13px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
      ctx!.textAlign = "center";
      ctx!.fillText("⚡ 3-SECOND VIRAL HOOK", width / 2, hookBoxY + 36);

      // Chữ Hook chính to, đậm, ngắt dòng tự động
      ctx!.fillStyle = "#FFFFFF";
      ctx!.font = "900 24px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
      wrapText(ctx!, hookTitle, width / 2, hookBoxY + 80, hookBoxW - 40, 34);

      // Điểm nhấn lợi ích dưới
      ctx!.fillStyle = "#A7F3D0";
      ctx!.font = "bold 15px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
      ctx!.fillText("🚀 Học thực hành • Làm được việc ngay", width / 2, hookBoxY + hookBoxH - 30);
      ctx!.restore();

      // 5. Animated Soundwave Bars (Sóng nhạc chuyển động sống động)
      ctx!.save();
      const waveY = height - 190;
      const numBars = 16;
      const barW = 6;
      const barGap = 6;
      const totalWaveW = numBars * (barW + barGap);
      const waveStartX = (width - totalWaveW) / 2;

      for (let i = 0; i < numBars; i++) {
        const barH = 12 + Math.sin(frame * 0.25 + i * 0.5) * 18 + Math.random() * 6;
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

      // 6. Brand Footer & Hotline
      ctx!.save();
      ctx!.fillStyle = "#E2E8F0";
      ctx!.font = "bold 15px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
      ctx!.textAlign = "center";
      ctx!.fillText(brand, width / 2, height - 100);

      ctx!.fillStyle = "#FDE047";
      ctx!.font = "800 16px -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
      ctx!.fillText(`📞 Hotline: ${hotline} • #Shorts #xuhuong`, width / 2, height - 70);
      ctx!.restore();

      frame++;
      requestAnimationFrame(drawFrame);
    }

    drawFrame();
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
