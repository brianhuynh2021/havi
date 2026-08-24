"""Application Service cho Roadmap Engine & Task Execution (Havi 3.0)."""

from datetime import UTC, datetime
from uuid import UUID

from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.goal_repository import GoalRepository
from adapters.persistence.roadmap_repository import RoadmapRepository
from core.enums import GoalCategory, ReviewDecision, RoadmapStatus, TaskOwnerType, TaskStatus
from core.events import EventLogEntry
from domain.models.goal import Goal
from domain.models.roadmap import EvidenceLog, Roadmap, RoadmapReview, RoadmapTask


class RoadmapService:
    def __init__(
        self,
        *,
        roadmap_repo: RoadmapRepository,
        goal_repo: GoalRepository,
        event_repo: EventLogRepository,
    ) -> None:
        self._roadmaps = roadmap_repo
        self._goals = goal_repo
        self._events = event_repo

    async def generate_roadmap_for_goal(
        self,
        *,
        workspace_id: UUID,
        goal_id: UUID,
    ) -> tuple[Roadmap, list[RoadmapTask]]:
        goal = await self._goals.get_by_id(workspace_id=workspace_id, goal_id=goal_id)
        if not goal:
            raise ValueError(f"Không tìm thấy mục tiêu {goal_id}")

        # Lưu trữ các roadmap cũ sang trạng thái SUPERSEDED
        await self._roadmaps.archive_existing_roadmaps(workspace_id=workspace_id, goal_id=goal_id)

        # Xây dựng cấu trúc đa tầng 90d -> 30d -> 7d -> Hôm nay theo danh mục
        h90, h30, h7, assumptions, task_templates = self._build_horizon_plan(goal)

        roadmap = await self._roadmaps.create_roadmap(
            workspace_id=workspace_id,
            goal_id=goal_id,
            title=f"Lộ trình thực hiện: {goal.title}",
            horizon_90d=h90,
            horizon_30d=h30,
            horizon_7d=h7,
            version=1,
            assumptions=assumptions,
            confidence_score=0.88,
            status=RoadmapStatus.ACTIVE.value,
        )

        tasks: list[RoadmapTask] = []
        for idx, tmpl in enumerate(task_templates):
            task = await self._roadmaps.create_task(
                workspace_id=workspace_id,
                roadmap_id=roadmap.id,
                goal_id=goal_id,
                title=tmpl["title"],
                why_this_is_next=tmpl["why_this_is_next"],
                done_rule=tmpl["done_rule"],
                description=tmpl.get("description"),
                time_estimate_minutes=tmpl.get("time_estimate_minutes", 30),
                owner_type=tmpl.get("owner_type", TaskOwnerType.COLLABORATIVE.value),
                capability_module=tmpl.get("capability_module", "manual"),
                inputs_needed=tmpl.get("inputs_needed"),
                fallback_action=tmpl.get("fallback_action"),
                order_index=idx,
            )
            tasks.append(task)

        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_kind="roadmap.generated",
                input_summary=f"Goal: {goal.title}",
                output_summary=f"Roadmap v1 created with {len(tasks)} initial tasks",
            )
        )

        return roadmap, tasks

    async def get_active_roadmap(
        self, *, workspace_id: UUID
    ) -> tuple[Roadmap | None, list[RoadmapTask]]:
        active_goal = await self._goals.get_active_goal(workspace_id=workspace_id)
        if not active_goal:
            return None, []
        roadmap = await self._roadmaps.get_active_roadmap(
            workspace_id=workspace_id, goal_id=active_goal.id
        )
        if not roadmap:
            return None, []
        tasks = await self._roadmaps.list_tasks_by_roadmap(
            workspace_id=workspace_id, roadmap_id=roadmap.id
        )
        return roadmap, tasks

    async def get_today_action(self, *, workspace_id: UUID) -> RoadmapTask | None:
        active_goal = await self._goals.get_active_goal(workspace_id=workspace_id)
        if not active_goal:
            return None
        roadmap = await self._roadmaps.get_active_roadmap(
            workspace_id=workspace_id, goal_id=active_goal.id
        )
        if not roadmap:
            return None
        return await self._roadmaps.get_next_recommended_task(
            workspace_id=workspace_id, roadmap_id=roadmap.id
        )

    async def complete_task_with_evidence(
        self,
        *,
        workspace_id: UUID,
        task_id: UUID,
        evidence_text: str,
        evidence_type: str = "note",
        value_number: float | None = None,
        media_asset_id: UUID | None = None,
    ) -> tuple[RoadmapTask, EvidenceLog]:
        task = await self._roadmaps.get_task_by_id(workspace_id=workspace_id, task_id=task_id)
        if not task:
            raise ValueError(f"Không tìm thấy nhiệm vụ {task_id}")

        updated_task = await self._roadmaps.update_task(
            task,
            status=TaskStatus.COMPLETED.value,
            completed_at=datetime.now(UTC),
            evidence_notes=evidence_text,
        )

        evidence = await self._roadmaps.create_evidence(
            workspace_id=workspace_id,
            goal_id=task.goal_id,
            task_id=task.id,
            source="task_completion",
            evidence_type=evidence_type,
            value_text=evidence_text,
            value_number=value_number,
            media_asset_id=media_asset_id,
            confidence=1.0,
        )

        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_kind="task.completed",
                input_summary=f"Task: {task.title}",
                output_summary=f"Completed with evidence: {evidence_text[:60]}",
            )
        )

        return updated_task, evidence

    async def block_task(
        self,
        *,
        workspace_id: UUID,
        task_id: UUID,
        reason: str,
        use_fallback: bool = False,
    ) -> RoadmapTask:
        task = await self._roadmaps.get_task_by_id(workspace_id=workspace_id, task_id=task_id)
        if not task:
            raise ValueError(f"Không tìm thấy nhiệm vụ {task_id}")

        new_status = TaskStatus.BLOCKED.value
        fallback_msg = task.fallback_action
        if use_fallback and task.fallback_action:
            new_status = TaskStatus.IN_PROGRESS.value

        updated_task = await self._roadmaps.update_task(
            task,
            status=new_status,
            evidence_notes=f"Lý do kẹt: {reason}",
            fallback_action=fallback_msg,
        )

        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_kind="task.blocked",
                input_summary=f"Task: {task.title}",
                output_summary=f"Reason: {reason[:60]} (fallback used: {use_fallback})",
            )
        )

        return updated_task

    async def reopen_task(
        self,
        *,
        workspace_id: UUID,
        task_id: UUID,
    ) -> RoadmapTask:
        task = await self._roadmaps.get_task_by_id(workspace_id=workspace_id, task_id=task_id)
        if not task:
            raise ValueError(f"Không tìm thấy nhiệm vụ {task_id}")

        updated_task = await self._roadmaps.update_task(
            task,
            status=TaskStatus.PENDING.value,
            completed_at=None,
            evidence_notes=None,
        )

        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_kind="task.reopened",
                input_summary=f"Task: {task.title}",
                output_summary="Reopened to pending status",
            )
        )

        return updated_task

    async def create_weekly_review(
        self,
        *,
        workspace_id: UUID,
        roadmap_id: UUID,
        completed_summary: str,
        evidence_summary: str,
        obstacles_summary: str,
        decision: str = ReviewDecision.CONTINUE.value,
        replan_diff: dict | None = None,
    ) -> RoadmapReview:
        roadmap = await self._roadmaps.get_roadmap_by_id(
            workspace_id=workspace_id, roadmap_id=roadmap_id
        )
        if not roadmap:
            raise ValueError("Không tìm thấy lộ trình")

        review = await self._roadmaps.create_review(
            workspace_id=workspace_id,
            goal_id=roadmap.goal_id,
            roadmap_id=roadmap_id,
            completed_summary=completed_summary,
            evidence_summary=evidence_summary,
            obstacles_summary=obstacles_summary,
            decision=decision,
            replan_diff=replan_diff,
            user_accepted=True,
        )

        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_kind="roadmap.reviewed",
                input_summary=f"Decision: {decision}",
                output_summary=f"Review logged for roadmap {roadmap_id}",
            )
        )

        return review

    async def list_roadmap_history(
        self, *, workspace_id: UUID, goal_id: UUID | None = None
    ) -> list[Roadmap]:
        return await self._roadmaps.list_roadmap_history(workspace_id=workspace_id, goal_id=goal_id)

    async def restore_roadmap_version(
        self,
        *,
        workspace_id: UUID,
        roadmap_id: UUID,
    ) -> tuple[Roadmap, list[RoadmapTask]]:
        target = await self._roadmaps.get_roadmap_by_id(
            workspace_id=workspace_id, roadmap_id=roadmap_id
        )
        if not target:
            raise ValueError(f"Không tìm thấy phiên bản lộ trình {roadmap_id}")

        history = await self._roadmaps.list_roadmap_history(
            workspace_id=workspace_id, goal_id=target.goal_id
        )
        max_version = max((r.version for r in history), default=1)

        # Lưu trữ phiên bản đang active
        await self._roadmaps.archive_existing_roadmaps(
            workspace_id=workspace_id, goal_id=target.goal_id
        )

        # Tạo phiên bản mới khôi phục từ target
        new_version = max_version + 1
        restored = await self._roadmaps.create_roadmap(
            workspace_id=workspace_id,
            goal_id=target.goal_id,
            title=f"{target.title} (Khôi phục từ v{target.version})",
            horizon_90d=target.horizon_90d,
            horizon_30d=target.horizon_30d,
            horizon_7d=target.horizon_7d,
            version=new_version,
            assumptions=target.assumptions,
            confidence_score=target.confidence_score,
            status=RoadmapStatus.ACTIVE.value,
        )

        old_tasks = await self._roadmaps.list_tasks_by_roadmap(
            workspace_id=workspace_id, roadmap_id=target.id
        )
        new_tasks: list[RoadmapTask] = []
        for idx, ot in enumerate(old_tasks):
            nt = await self._roadmaps.create_task(
                workspace_id=workspace_id,
                roadmap_id=restored.id,
                goal_id=target.goal_id,
                title=ot.title,
                why_this_is_next=ot.why_this_is_next,
                done_rule=ot.done_rule,
                description=ot.description,
                time_estimate_minutes=ot.time_estimate_minutes,
                owner_type=ot.owner_type,
                capability_module=ot.capability_module,
                inputs_needed=ot.inputs_needed,
                fallback_action=ot.fallback_action,
                order_index=idx,
            )
            new_tasks.append(nt)

        await self._events.record(
            EventLogEntry(
                workspace_id=workspace_id,
                job_kind="roadmap.restored",
                input_summary=f"Restored from v{target.version}",
                output_summary=f"Created active v{new_version} with {len(new_tasks)} tasks",
            )
        )

        return restored, new_tasks

    async def list_evidence(
        self, *, workspace_id: UUID, goal_id: UUID | None = None
    ) -> list[EvidenceLog]:
        return await self._roadmaps.list_evidence(workspace_id=workspace_id, goal_id=goal_id)

    async def list_reviews(
        self, *, workspace_id: UUID, goal_id: UUID | None = None
    ) -> list[RoadmapReview]:
        return await self._roadmaps.list_reviews(workspace_id=workspace_id, goal_id=goal_id)

    def _build_horizon_plan(self, goal: Goal) -> tuple[str, str, str, list[str], list[dict]]:
        category = goal.category
        title = goal.title

        # Wedge 1: Local Opportunity Loop (Training Center, Spa, Salon, Clinic, Resort/Homestay, Garage)
        if category in [GoalCategory.ACQUIRE_CUSTOMERS.value, GoalCategory.LAUNCH.value]:
            h90 = f"Xây dựng dòng khách hàng đều đặn mỗi tuần cho '{title}', đo lường qua {goal.evidence_definition or 'lượt khách/học viên/đặt phòng xác nhận'}."
            h30 = "Xác thực gói ưu đãi cốt lõi, hoàn thiện kịch bản chuyển đổi và tiếp cận 100 khách hàng tiềm năng đầu tiên."
            h7 = "Thiết lập thông điệp thu hút, triển khai 3 bài viết/video ngắn đầu tiên và trực tin nhắn phản hồi <10s."
            assumptions = [
                "Khách hàng địa phương/du khách quan tâm đến chất lượng thật và ưu đãi trải nghiệm đầu tiên.",
                "Tốc độ phản hồi nhanh < 10s giúp nắm bắt trọn vẹn sự chú ý của khách hàng ngay khi có nhu cầu.",
            ]

            task_templates = [
                {
                    "title": "Soạn thông điệp & Ưu đãi trải nghiệm đầu tiên",
                    "why_this_is_next": "Cần có lời mời rõ ràng, không thể chối từ trước khi bắt đầu tiếp cận khách hàng.",
                    "done_rule": "Có 1 bài viết hoặc video ngắn nêu rõ ưu đãi, giá và thời hạn.",
                    "time_estimate_minutes": 25,
                    "owner_type": TaskOwnerType.COLLABORATIVE.value,
                    "capability_module": "content",
                    "inputs_needed": "Hình ảnh/video thật tại cơ sở",
                    "fallback_action": "Dùng 1 bài viết văn bản ngắn nêu rõ ưu đãi trước.",
                },
                {
                    "title": "Quay video 15s bằng điện thoại có máy nhắc chữ",
                    "why_this_is_next": "Video ngắn 9:16 truyền tải trực quan và chân thực không gian, dịch vụ tại cơ sở.",
                    "done_rule": "Clip 15-30s rõ mặt, rõ âm thanh và có hook 3 giây đầu.",
                    "time_estimate_minutes": 20,
                    "owner_type": TaskOwnerType.USER.value,
                    "capability_module": "video",
                    "fallback_action": "Chụp 3 bức ảnh thật tại cơ sở kèm bảng giá.",
                },
                {
                    "title": "Duyệt & Đăng bài lên Facebook Fanpage & Google Maps",
                    "why_this_is_next": "Đưa thông điệp ra kênh tiếp cận người dùng địa phương.",
                    "done_rule": "Bài viết được duyệt và lên lịch xuất bản thành công.",
                    "time_estimate_minutes": 10,
                    "owner_type": TaskOwnerType.COLLABORATIVE.value,
                    "capability_module": "content",
                },
                {
                    "title": "Bật chuông báo Hot Lead Radar về Telegram",
                    "why_this_is_next": "Đảm bảo không bỏ lỡ bất kỳ khách hàng nào để lại số điện thoại.",
                    "done_rule": "Nhận được tin nhắn test chuông báo trên Telegram.",
                    "time_estimate_minutes": 5,
                    "owner_type": TaskOwnerType.USER.value,
                    "capability_module": "inbox",
                },
            ]

        # Wedge 2: Professional Opportunity Loop — Headhunter / Recruiter on LinkedIn
        elif category in [GoalCategory.RECRUIT.value, GoalCategory.GROW_AUDIENCE.value]:
            h90 = f"Xây dựng vị thế chuyên môn uy tín, mở rộng mạng lưới và chốt 3-5 Job Orders/Placements mới cho '{title}'."
            h30 = "Chia sẻ 12 câu chuyện nghề nghiệp/case study thực tế, tạo 30 cuộc hội thoại chất lượng (Qualified Conversations)."
            h7 = "Thu âm 1 Voice Note câu chuyện tuyển dụng thực tế, tạo 2 bài viết phân tích chuyên sâu và kết nối 10 Hiring Managers."
            assumptions = [
                "Câu chuyện thực tế về thị trường lao động và ca giải cứu tuyển dụng tạo độ tin cậy cao nhất với doanh nghiệp.",
                "Hội thoại 1-1 mang tính tư vấn chuyển đổi thành Job Order hiệu quả hơn chào hàng lạnh.",
            ]
            task_templates = [
                {
                    "title": "Thu âm Voice Note 3 phút về một ca tuyển dụng thành công hoặc bài học nghề",
                    "why_this_is_next": "Câu chuyện thực tế đời thường giúp Havi trích xuất góc nhìn sâu sắc mà bạn không phải ngồi gõ phím.",
                    "done_rule": "Có 1 bản ghi âm 2-3 phút nêu rõ bối cảnh, khó khăn của ứng viên/doanh nghiệp và cách xử lý.",
                    "time_estimate_minutes": 10,
                    "owner_type": TaskOwnerType.USER.value,
                    "capability_module": "manual",
                    "fallback_action": "Ghi chú 3 gạch đầu dòng về ca tuyển dụng đáng nhớ gần nhất.",
                },
                {
                    "title": "Duyệt & Đăng bài viết góc nhìn chuyên gia lên LinkedIn",
                    "why_this_is_next": "Duy trì tần suất hiện diện chuyên nghiệp để khách hàng và ứng viên nhớ đến khi có nhu cầu.",
                    "done_rule": "Bài viết được duyệt với thông điệp rõ ràng và CTA mời trao đổi góc nhìn.",
                    "time_estimate_minutes": 15,
                    "owner_type": TaskOwnerType.COLLABORATIVE.value,
                    "capability_module": "content",
                },
                {
                    "title": "Gửi lời mời kết nối kèm tin nhắn cá nhân hoá tới 10 Hiring Manager mục tiêu",
                    "why_this_is_next": "Chủ động mở rộng mạng lưới người có quyền quyết định tuyển dụng trong ngành mục tiêu.",
                    "done_rule": "Gửi 10 lời mời kèm ghi chú ngắn gọn, liên quan đến chuyên môn.",
                    "time_estimate_minutes": 20,
                    "owner_type": TaskOwnerType.USER.value,
                    "capability_module": "manual",
                },
                {
                    "title": "Ghi nhận cuộc gọi trao đổi chuyên sâu (Client/Candidate Discovery Call)",
                    "why_this_is_next": "Chuyển hội thoại mạng xã hội thành cơ hội tuyển dụng/hợp tác thực tế.",
                    "done_rule": "Ghi nhận tóm tắt nhu cầu tuyển dụng hoặc kỳ vọng của ứng viên vào Bằng chứng.",
                    "time_estimate_minutes": 30,
                    "owner_type": TaskOwnerType.USER.value,
                    "capability_module": "manual",
                },
            ]

        # Wedge 3: Professional Opportunity Loop — B2B Consultant / Freelance Developer
        elif category in [GoalCategory.SELL_OFFER.value, GoalCategory.DELIVER_PROJECT.value]:
            h90 = f"Xây dựng pipeline dự án B2B vững chắc, ký kết 2-3 hợp đồng tư vấn/triển khai giá trị cao cho '{title}'."
            h30 = "Đóng gói Case Study kết quả dự án mẫu, tiếp cận 30 đối tác tiềm năng và gửi 5 bản đề xuất (Proposals)."
            h7 = "Soạn Case Study giải quyết bài toán kỹ thuật/kinh doanh thực tế (1 trang) và tiếp cận 5 khách hàng tiềm năng."
            assumptions = [
                "Khách hàng B2B ra quyết định dựa trên bằng chứng kết quả cụ thể (Case study) hơn là lời hứa hẹn chung chung.",
                "Discovery Call giúp định hình đúng phạm vi dự án và nâng cao tỷ lệ chốt hợp đồng.",
            ]
            task_templates = [
                {
                    "title": "Soạn Case Study 1 trang: Bài toán thực tế -> Giải pháp -> Kết quả đo lường",
                    "why_this_is_next": "Cần tài liệu bằng chứng xác thực để gửi cho khách hàng tiềm năng khi họ quan tâm.",
                    "done_rule": "File Case Study nêu rõ số liệu cải thiện (thời gian, chi phí, doanh thu hoặc hiệu năng).",
                    "time_estimate_minutes": 30,
                    "owner_type": TaskOwnerType.COLLABORATIVE.value,
                    "capability_module": "manual",
                    "fallback_action": "Viết 1 đoạn tóm tắt ngắn 150 chữ về một dự án vừa bàn giao thành công.",
                },
                {
                    "title": "Tiếp cận 5 khách hàng tiềm năng bằng thông điệp tư vấn giải pháp",
                    "why_this_is_next": "Chủ động đề xuất góc nhìn giải quyết vấn đề cho đối tác.",
                    "done_rule": "Gửi 5 thông điệp tư vấn cá nhân hoá kèm liên kết Case Study.",
                    "time_estimate_minutes": 25,
                    "owner_type": TaskOwnerType.USER.value,
                    "capability_module": "manual",
                },
                {
                    "title": "Thực hiện cuộc gọi Discovery Call 30 phút và gửi Bản đề xuất (Proposal)",
                    "why_this_is_next": "Làm rõ yêu cầu kỹ thuật/kinh doanh và thống nhất phạm vi công việc.",
                    "done_rule": "Gửi bản đề xuất dự án kèm cam kết tiến độ và ngân sách.",
                    "time_estimate_minutes": 45,
                    "owner_type": TaskOwnerType.USER.value,
                    "capability_module": "manual",
                },
            ]

        else:
            h90 = f"Hoàn thành toàn diện mục tiêu '{title}' với bằng chứng đo lường xác thực."
            h30 = "Đạt 50% khối lượng công việc và kiểm tra phản hồi thực tế từ người dùng/thị trường."
            h7 = "Xác định 3 đầu việc quan trọng nhất tuần này và bắt đầu ngay việc đầu tiên."
            assumptions = ["Tập trung vào 1 hành động duy nhất mỗi ngày giúp tránh quá tải."]
            task_templates = [
                {
                    "title": "Xác định tiêu chí hoàn thành & Nguồn lực cần thiết",
                    "why_this_is_next": "Làm rõ bằng chứng kết quả để không bị phân tâm.",
                    "done_rule": "Ghi nhận rõ ràng kết quả cụ thể mong muốn đạt được.",
                    "time_estimate_minutes": 20,
                    "owner_type": TaskOwnerType.COLLABORATIVE.value,
                    "capability_module": "manual",
                },
                {
                    "title": "Thực hiện hành động bước 1 và ghi nhận bằng chứng",
                    "why_this_is_next": "Hành động thực tế tạo ra kết quả để Havi đánh giá lại lộ trình.",
                    "done_rule": "Đính kèm ghi chú hoặc kết quả cụ thể sau khi hoàn tất.",
                    "time_estimate_minutes": 30,
                    "owner_type": TaskOwnerType.USER.value,
                    "capability_module": "manual",
                },
            ]

        return h90, h30, h7, assumptions, task_templates
