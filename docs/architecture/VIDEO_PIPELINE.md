# Havi Video Pipeline

> **Havi does not render, edit, or caption video.** It accepts a clip the shop
> owner already made and publishes it to Facebook Reels — reliably, once, and
> with proof it actually landed.

```text
Upload clip (chủ tiệm tự quay & tự cắt bằng CapCut)
  ↓
MediaService.complete_upload — ffprobe reads duration / dimensions / audio
  ↓
video_constraints.check_video_for_channel — 9:16? 3–90s? has audio?
  │  ✗ rejected here, at upload time, while the owner can still reshoot
  ↓
VideoPost (READY_FOR_REVIEW) — caption + channel + source clip
  ↓
human approves  ──►  APPROVED  ──►  PUBLISHING
  ↓
FacebookPublisher._post_reel — start / upload / finish
  ↓
VERIFYING — read the Page back
  │  ✗ lost the thread → PENDING_RECONCILIATION (reconcile, never resend)
  ↓
PUBLISHED — confirmed present on the Page
```

## Why the render engine was removed (2026-08-25)

An earlier design put an AI edit engine between upload and publish: multimodal
video understanding, a transcript engine, `EditPlan.json`, an FFmpeg renderer, a
Remotion renderer, a safe-zone checker, and a quality gate. Roughly 5,000 lines
of non-test Python, plus a 689-line canvas renderer in the browser.

It was cut for three reasons:

1. **It competed where Havi cannot win.** Shop owners already use CapCut daily
   and are faster in it than any web editor Havi could ship.
2. **It was the largest source of operational risk.** FFmpeg on the server,
   demo/mock renderers that had to be fenced off from production, a nine-state
   render machine, and three migrations — all upstream of the one thing that
   actually mattered: the post landing on the Page.
3. **Its core was never real.** `VideoAIDirector.generate_manifest` returned the
   same rule-based manifest on both branches of its `if`; the "AI direction" was
   a TODO wearing a class name.

The code is in git history. If the decision is reversed, recover it from the
commit that removed it rather than rewriting from this document.

## What remains, and why each piece exists

| Piece | Job |
|---|---|
| `domain/policies/video_constraints.py` | Per-channel rules (aspect, duration, audio). Pure policy, no I/O. Checked **at upload**, not at publish — a clip rejected at 8pm on Saturday cannot be reshot. |
| `domain/models/video_post.py` | One row per clip heading for a Page. Holds `source_object_key` so publishing needs no join. |
| `domain/policies/video_job_state.py` | The legal transitions. `PENDING_RECONCILIATION → PUBLISHING` does not exist, and that absence is the anti-duplicate guarantee. |
| `application/services/video_post_service.py` | Upload → validate → create. Returns *every* rejection reason at once. |
| `application/services/video_publish_service.py` | Approve → publish → verify → reconcile. No path reaches `PUBLISHED` without reading the platform back. |
| `adapters/persistence/video_publish_repository.py` | Partial unique index on live attempts. Duplicate prevention lives in Postgres, not in an `if`. |
| `adapters/publishers/facebook.py` | Graph API: `/feed`, `/photos`, album, and the three-phase `video_reels` upload; plus `verify_reel`. |

## The two rules that everything else serves

**1. No path to `PUBLISHED` without reading the platform back.** A 200 from the
Reels `finish` phase means Facebook accepted the job, not that the video is on
the Page — Reels processes asynchronously and can still fail afterwards.

**2. Lost the thread? Reconcile, never resend.** Every failure *after* Facebook
issues a `video_id` is ambiguous. Resending there is the most reliable way to
put two identical Reels on a customer's Page, and that cannot be undone.

## Tests

```bash
cd apps/backend
uv run pytest tests/test_video_ingestion.py        # ffprobe + channel constraints (needs ffmpeg)
uv run pytest tests/test_video_post_service.py     # upload → validate → queue
uv run pytest tests/test_video_publish_flow.py     # approve → publish → verify → reconcile
uv run pytest tests/test_facebook_publish_routes.py # which Graph endpoint, which post id
```
