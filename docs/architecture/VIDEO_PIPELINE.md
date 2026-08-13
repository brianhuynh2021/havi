# Havi Video Pipeline Architecture (Phase 3)

> Short-form AI Video Processing, Transcript, AI Edit Planning, and Rendering Engine for Reels, TikTok, and YouTube Shorts.

```text
Upload (Raw Video)
  ↓
Video Understanding
  ├─ Gemini 2.5 Multimodal
  ├─ OpenAI Vision
  └─ Provider Router Fallback
  ↓
Transcript Engine
  ├─ Whisper / WhisperX (Word-level timestamps & VAD)
  └─ Alternative STT APIs
  ↓
AI Edit Engine ⭐
  ↓
EditPlan.json (Cuts, Captions, Highlights, B-Roll, Overlays)
  ↓
Renderer
  ├─ FFmpeg (Default headless CLI renderer)
  ├─ Remotion (React-driven motion graphics & animated captions)
  └─ Cloud Rendering Workers
  ↓
Final Reel / TikTok / YouTube Short
```

---

## 1. Pipeline Stages & Boundaries

### 1. Upload & Ingestion
- Raw video uploaded directly to object storage via presigned tickets (`MediaType.VIDEO`).
- `FFmpegVideoProcessor` probes metadata: duration, resolution (1080x1920), FPS, aspect ratio (9:16 classification), and audio stream presence.

### 2. Video Understanding & Multimodal Analysis
- Multi-provider LLM router (`Gemini 2.5 Flash` / `OpenAI`) analyzes keyframes and visual highlights.
- Identifies visual hooks, key product moments, facial gestures, and aesthetic scene boundaries.

### 3. Transcript & Subtitle Alignment
- Speech-to-text (`WhisperX`) generates exact word-level timecodes (`start_ms`, `end_ms`).
- Detects speaker pauses, filler words, and sentence boundaries for tight cuts.

### 4. AI Edit Engine & `EditPlan.json`
- Generates a structured execution plan (`EditPlan.json`):
  ```json
  {
    "target_aspect_ratio": "9:16",
    "target_duration_seconds": 30,
    "cuts": [
      {"start_ms": 1200, "end_ms": 5400, "zoom_scale": 1.1},
      {"start_ms": 6800, "end_ms": 14200, "zoom_scale": 1.0}
    ],
    "captions": [
      {"text": "BÍ QUYẾT GỘI ĐẦU DƯỠNG SINH", "start_ms": 1200, "end_ms": 3500, "style": "bold_yellow_highlight"}
    ],
    "audio": {
      "normalize_db": -14,
      "bg_music_volume": 0.15
    }
  }
  ```

### 5. Video Rendering Engine
- **FFmpeg Renderer (Default)**: Concat filters, drawtext caption rendering, crop/scale to 9:16 vertical, audio normalization.
- **Remotion Renderer**: React component motion graphics for animated kinetic typography, lower thirds, and brand logo stings.

### 6. Channel Dispatch
- Final `.mp4` video dispatched to Facebook Reels, TikTok API, or YouTube Shorts API via background Celery publish workers.
