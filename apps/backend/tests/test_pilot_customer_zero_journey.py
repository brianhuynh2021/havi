"""End-to-End Customer Zero (Trung Tâm Nhật Minh) & Local Pilot Journey Tests (Havi 3.0 Phase 4).

Validates the full 30-day lifecycle across 4 distinct Goal Archetypes:
1. Acquire Customers (Nhật Minh training center student cohort)
2. Launch (Boutique Resort / Homestay direct booking campaign)
3. Sell Offer (Spa / Clinic high-ticket package)
4. Deliver Project (Local service milestone delivery)
"""

from httpx import AsyncClient


async def _signup_and_get_workspace(
    client: AsyncClient, *, email: str, name: str, ws_name: str, industry: str
):
    signup = await client.post(
        "/auth/sign-up", json={"name": name, "email": email, "password": "matkhau123"}
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()
    headers = {"Authorization": f"Bearer {token_pair['access_token']}"}

    create_ws = await client.post(
        "/workspaces",
        json={"name": ws_name, "industry": industry},
        headers=headers,
    )
    assert create_ws.status_code == 201, create_ws.text
    ws_id = create_ws.json()["id"]

    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    assert refreshed.status_code == 200
    new_headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    return new_headers, ws_id


async def test_customer_zero_nhat_minh_30day_journey(client: AsyncClient):
    """Mô phỏng trọn vẹn vòng lặp Customer Zero tại Trung Tâm Nhật Minh."""
    headers, _ = await _signup_and_get_workspace(
        client,
        email="nhatminh_c0@havi.vn",
        name="Thầy Minh (Customer Zero)",
        ws_name="Trung Tâm Công Nghệ Nhật Minh",
        industry="education",
    )

    # 1. Khởi tạo Mục tiêu 30 ngày: Tuyển sinh 20 học viên khóa Lập trình AI
    goal_res = await client.post(
        "/goals",
        json={
            "title": "Tuyển sinh 20 học viên khóa Lập trình AI ứng dụng",
            "category": "acquire_customers",
            "evidence_definition": "Học viên đóng học phí xác nhận qua VietQR",
            "weekly_capacity_hours": 12,
        },
        headers=headers,
    )
    assert goal_res.status_code == 201
    goal = goal_res.json()
    goal_id = goal["id"]

    # 2. Sinh Lộ Trình đa tầng (90d / 30d / 7d)
    roadmap_res = await client.post(
        "/roadmaps/generate", json={"goal_id": goal_id}, headers=headers
    )
    assert roadmap_res.status_code == 201
    roadmap_data = roadmap_res.json()
    roadmap_id = roadmap_data["roadmap"]["id"]
    assert len(roadmap_data["tasks"]) >= 3

    # 3. Thực hiện Tuần 1: Việc hôm nay -> Hoàn thành kèm bằng chứng (Evidence 1)
    today_res = await client.get("/roadmaps/today", headers=headers)
    assert today_res.status_code == 200
    task1 = today_res.json()

    done1 = await client.post(
        f"/roadmaps/tasks/{task1['id']}/complete",
        json={
            "evidence_text": "Đã quay 1 video lớp học thực tế 15s và soạn bài ưu đãi khóa AI",
            "evidence_type": "note",
            "value_number": 1.0,
        },
        headers=headers,
    )
    assert done1.status_code == 200

    # 4. Review Tuần 1 (Weekly Review 1): Đánh giá tiếp tục
    rev1 = await client.post(
        f"/roadmaps/{roadmap_id}/review",
        json={
            "completed_summary": "Đã đăng bài viết và nhận 8 tin nhắn hỏi lịch học",
            "evidence_summary": "Có 2 phụ huynh đặt cọc giữ chỗ qua VietQR",
            "obstacles_summary": "Tốc độ trả lời tư vấn buổi tối còn chậm",
            "decision": "continue",
        },
        headers=headers,
    )
    assert rev1.status_code == 200
    assert rev1.json()["decision"] == "continue"

    # 5. Thực hiện Tuần 2: Gặp trở ngại & dùng Fallback Task
    today_res2 = await client.get("/roadmaps/today", headers=headers)
    assert today_res2.status_code == 200
    task2 = today_res2.json()

    block_res = await client.post(
        f"/roadmaps/tasks/{task2['id']}/block",
        json={"reason": "Chưa kịp quay video mới", "use_fallback": True},
        headers=headers,
    )
    assert block_res.status_code == 200

    # 6. Review Tuần 2: Cải tiến (Improve) -> Tự động sinh roadmap v2
    rev2 = await client.post(
        f"/roadmaps/{roadmap_id}/review",
        json={
            "completed_summary": "Đã dùng ảnh chụp lớp học thay cho video",
            "evidence_summary": "Đã tuyển thêm 5 học viên chính thức (tổng cộng 7/20)",
            "obstacles_summary": "Cần thêm bài viết chia sẻ cảm nhận học viên cũ",
            "decision": "improve",
        },
        headers=headers,
    )
    assert rev2.status_code == 200
    assert rev2.json()["decision"] == "improve"

    # 7. Kiểm tra Lịch sử Roadmap (Phải có ít nhất 1 phiên bản được lưu trữ)
    history_res = await client.get("/roadmaps/history", headers=headers)
    assert history_res.status_code == 200
    assert len(history_res.json()) >= 1

    # 8. Kiểm tra Dòng Bằng Chứng (Evidence Stream)
    evidence_res = await client.get("/roadmaps/evidence", headers=headers)
    assert evidence_res.status_code == 200
    assert len(evidence_res.json()) >= 1


async def test_local_hospitality_resort_journey(client: AsyncClient):
    """Mô phỏng vòng lặp Direct Booking cho Boutique Resort / Homestay nghỉ dưỡng."""
    headers, _ = await _signup_and_get_workspace(
        client,
        email="resort_pilot@havi.vn",
        name="Chủ Resort An Nhiên",
        ws_name="An Nhiên Eco Resort & Villa",
        industry="local_service",
    )

    # Khởi tạo mục tiêu kéo khách đặt phòng trực tiếp không qua OTA
    goal_res = await client.post(
        "/goals",
        json={
            "title": "Lấp đầy 30 đêm phòng trực tiếp (Direct Booking) trong tháng",
            "category": "acquire_customers",
            "evidence_definition": "Khách chuyển khoản cọc phòng qua VietQR",
            "weekly_capacity_hours": 10,
        },
        headers=headers,
    )
    assert goal_res.status_code == 201
    goal_id = goal_res.json()["id"]

    # Sinh lộ trình
    roadmap_res = await client.post(
        "/roadmaps/generate", json={"goal_id": goal_id}, headers=headers
    )
    assert roadmap_res.status_code == 201
    roadmap_data = roadmap_res.json()
    assert (
        "đặt phòng" in roadmap_data["roadmap"]["horizon_90d"]
        or "khách hàng" in roadmap_data["roadmap"]["horizon_90d"]
    )
