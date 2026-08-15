"""Các job của worker — khung rỗng, điền khi nối LLM và adapter thật.

Phễu listening (tiết kiệm token): 100% bài → keyword + rule (0 token) → ~5% → model rẻ
chấm điểm ý định → ~1% → LLM soạn trả lời → dừng ở pending_approval.
"""

import asyncio
import logging
from uuid import UUID

from application.services.content_engine import GenerationFailed
from application.services.content_service import ContentJobNotFound, WorkspaceNotFound
from core.request_context import reset_request_id, set_request_id
from worker.celery_app import celery_app

logger = logging.getLogger("havi.worker.tasks")


@celery_app.task(name="havi.content.generate_drafts", bind=True, max_retries=3)
def generate_drafts(self, workspace_id: str, job_id: str, request_id: str | None = None) -> None:  # noqa: ANN001
    """Ingest media → đọc brand profile → 1 lần gọi LLM sinh mọi kênh.

    Trạng thái draft khi sinh xong lấy từ `core.content_state.initial_status(publish_mode)`.

    Không Celery-retry khi `GenerationFailed`: ProviderRouter đã thử lần lượt mọi
    provider được cấu hình rồi mới ném lỗi này, nên retry cùng prompt gần như chỉ
    lặp lại thất bại và tốn thêm tiền. Job đã được đánh `failed` kèm reason để chủ
    tiệm thấy và bấm tạo lại nếu muốn. Celery retry vẫn giữ cho lỗi hạ tầng
    (DB/Redis mất kết nối) — những lỗi đó thoát ra ngoài như exception khác.
    """
    from worker.content_engine_factory import content_engine_scope

    async def _run() -> None:
        ws_id = UUID(workspace_id)
        j_id = UUID(job_id)
        for attempt in range(3):
            try:
                async with content_engine_scope() as engine:
                    await engine.generate_drafts(workspace_id=ws_id, job_id=j_id)
                    return
            except ContentJobNotFound:
                if attempt < 2:
                    await asyncio.sleep(0.3)
                else:
                    raise

    token = set_request_id(request_id) if request_id else None
    try:
        try:
            asyncio.run(_run())
        except (GenerationFailed, ContentJobNotFound, WorkspaceNotFound) as exc:
            logger.warning("Worker skipping job %s (%s)", job_id, type(exc).__name__)
            return
    finally:
        if token is not None:
            reset_request_id(token)


@celery_app.task(name="havi.listening.classify", bind=True)
def classify_listening_item(self, inbox_item_id: str) -> None:  # noqa: ANN001
    """Rule + model nhỏ chấm điểm ý định trước khi động tới LLM xịn."""
    del self, inbox_item_id
    raise NotImplementedError


@celery_app.task(name="havi.reply.draft", bind=True)
def draft_reply(self, inbox_item_id: str) -> None:  # noqa: ANN001
    """Soạn `ai_suggested_reply`. Luôn dừng ở pending_approval — không tự gửi."""
    del self, inbox_item_id
    raise NotImplementedError


@celery_app.task(name="havi.publish.run_due", max_retries=0)
def publish_run_due(limit: int = 20) -> int:
    """Chạy các publish job đã đến hạn. Trả số job đã nhận trong lượt này.

    Không nhận `content_item_id`: job được nhận bằng `claim_due`
    (`FOR UPDATE SKIP LOCKED`) chứ không bằng tham số của message. Đó là chủ ý —
    nếu id nằm trong message thì Celery giao lại một message (điều nó *được phép*
    làm với `task_acks_late`) là hai worker cùng đăng một bài. Khoá phải ở
    Postgres, không ở hàng đợi.

    Retry cũng không do Celery: `mark_failed` xếp lịch thử lại theo
    `PublishFailureKind` (temporary → backoff 60/300/900s; auth_permission và
    validation_permanent → dead-letter ngay). Thêm `max_retries` của Celery lên
    trên là hai cơ chế retry lệch nhau trên cùng một job.
    """
    from worker.publish_service_factory import publish_service_scope

    async def _run() -> int:
        async with publish_service_scope() as service:
            return len(await service.run_due(limit=limit))

    return asyncio.run(_run())


@celery_app.task(name="havi.video.render", bind=True, max_retries=1)
def render_video_job(self, workspace_id: str, job_id: str, request_id: str | None = None) -> None:  # noqa: ANN001
    """Thực thi pipeline render video bất đồng bộ qua hàng đợi Celery.

    Chạy trên hàng đợi riêng `havi.video_render` để không nghẽn các tác vụ nhẹ.
    """
    import os
    import tempfile

    from core.enums import MediaStatus, MediaType
    from worker.video_render_factory import video_render_scope

    async def _run() -> None:
        ws_id = UUID(workspace_id)
        j_id = UUID(job_id)

        async with video_render_scope() as ctx:
            job = await ctx.render_repo.get(workspace_id=ws_id, job_id=j_id)
            if not job:
                logger.warning("VideoRenderJob %s not found", job_id)
                return

            await ctx.render_repo.set_rendering(job_id=j_id)

            with tempfile.TemporaryDirectory() as tmp_dir:
                source_path = os.path.join(tmp_dir, "source.mp4")
                output_path = os.path.join(tmp_dir, "rendered.mp4")

                # 1. Tải source asset nếu có
                if job.source_media_id:
                    source_asset = await ctx.media_repo.get(
                        workspace_id=ws_id, asset_id=job.source_media_id
                    )
                    if source_asset:
                        try:
                            video_bytes = ctx.storage.get_bytes(source_asset.object_key)
                            with open(source_path, "wb") as f:
                                f.write(video_bytes)
                        except Exception as exc:
                            logger.error(
                                "Failed to download source video %s: %s",
                                source_asset.object_key,
                                exc,
                            )
                            await ctx.render_repo.fail(
                                job_id=j_id, error_message=f"Failed to load source video: {exc}"
                            )
                            return

                # Nếu không có source asset, tạo clip nền mặc định
                if not os.path.exists(source_path):
                    with open(source_path, "wb") as f:
                        f.write(b"MOCK_SOURCE_VIDEO_BYTES")

                # 2. Callback cập nhật tiến độ
                async def progress_cb(pct: int) -> None:
                    await ctx.render_repo.update_progress(job_id=j_id, progress_percent=pct)

                # 3. Thực thi Render
                try:
                    render_result = await ctx.renderer.render(
                        job_id=j_id,
                        edit_plan=job.edit_plan,
                        source_video_path=source_path,
                        output_video_path=output_path,
                        progress_callback=progress_cb,
                    )
                except Exception as exc:
                    logger.exception("Render video job %s failed", job_id)
                    await ctx.render_repo.fail(job_id=j_id, error_message=str(exc))
                    return

                # 4. Upload video output lên Object Storage
                output_key = f"workspaces/{ws_id}/rendered_videos/{j_id}.mp4"
                thumbnail_key = f"workspaces/{ws_id}/rendered_videos/{j_id}_thumb.jpg"

                with open(render_result.output_file_path, "rb") as f:
                    rendered_bytes = f.read()

                ctx.storage.put_bytes(
                    object_key=output_key,
                    data=rendered_bytes,
                    content_type="video/mp4",
                )

                if render_result.thumbnail_file_path and os.path.exists(
                    render_result.thumbnail_file_path
                ):
                    with open(render_result.thumbnail_file_path, "rb") as f:
                        thumb_bytes = f.read()
                    ctx.storage.put_bytes(
                        object_key=thumbnail_key,
                        data=thumb_bytes,
                        content_type="image/jpeg",
                    )
                else:
                    thumbnail_key = None

                # 5. Tạo bản ghi MediaAsset
                media_asset = await ctx.media_repo.create(
                    workspace_id=ws_id,
                    object_key=output_key,
                    filename=f"{job.title}.mp4",
                    content_type="video/mp4",
                    type=MediaType.VIDEO,
                )
                media_asset.status = MediaStatus.RAW
                media_asset.duration_seconds = render_result.duration_seconds
                media_asset.width = render_result.width
                media_asset.height = render_result.height
                media_asset.aspect_ratio = job.target_aspect_ratio
                media_asset.has_audio = True
                media_asset.thumbnail_object_key = thumbnail_key
                media_asset.size_bytes = len(rendered_bytes)

                # 6. Đánh dấu hoàn tất
                public_url = ctx.storage.public_url(output_key)
                await ctx.render_repo.complete(
                    job_id=j_id,
                    output_media_id=media_asset.id,
                    output_url=public_url,
                )

    token = set_request_id(request_id) if request_id else None
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(asyncio.run, _run()).result()
        else:
            asyncio.run(_run())
    finally:
        if token is not None:
            reset_request_id(token)
