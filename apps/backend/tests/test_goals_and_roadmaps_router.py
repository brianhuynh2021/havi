"""API integration tests cho /goals và /roadmaps routers (Havi 3.0)."""

from httpx import AsyncClient


async def _sign_up_and_create_workspace(
    client: AsyncClient, *, email: str, name: str = "Thầy Minh"
) -> tuple[dict, str]:
    signup = await client.post(
        "/auth/sign-up", json={"name": name, "email": email, "password": "matkhau123"}
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()
    headers = {"Authorization": f"Bearer {token_pair['access_token']}"}

    create_ws = await client.post(
        "/workspaces",
        json={"name": "Trung Tâm Nhật Minh", "industry": "education"},
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


async def test_goals_and_roadmaps_api_flow(client: AsyncClient):
    headers, _ = await _sign_up_and_create_workspace(client, email="goal_api@havi.vn")

    # 1. Tạo mục tiêu mới
    goal_res = await client.post(
        "/goals",
        json={
            "title": "Tuyển sinh 20 học viên khóa Lập trình AI",
            "category": "acquire_customers",
            "evidence_definition": "Học viên xác nhận đóng học phí qua VietQR",
            "weekly_capacity_hours": 15,
        },
        headers=headers,
    )
    assert goal_res.status_code == 201, goal_res.text
    goal = goal_res.json()
    assert goal["title"] == "Tuyển sinh 20 học viên khóa Lập trình AI"
    assert goal["status"] == "active"
    goal_id = goal["id"]

    # 2. Lấy active goal
    active_res = await client.get("/goals/active", headers=headers)
    assert active_res.status_code == 200
    assert active_res.json()["id"] == goal_id

    # 3. Sinh lộ trình thực hiện (Roadmap)
    roadmap_res = await client.post(
        "/roadmaps/generate",
        json={"goal_id": goal_id},
        headers=headers,
    )
    assert roadmap_res.status_code == 201, roadmap_res.text
    data = roadmap_res.json()
    assert data["roadmap"]["goal_id"] == goal_id
    assert len(data["tasks"]) >= 3
    first_task = data["tasks"][0]

    # 4. Lấy hành động đề xuất hôm nay
    today_res = await client.get("/roadmaps/today", headers=headers)
    assert today_res.status_code == 200
    assert today_res.json()["id"] == first_task["id"]

    # 5. Hoàn thành nhiệm vụ kèm bằng chứng (Evidence)
    complete_res = await client.post(
        f"/roadmaps/tasks/{first_task['id']}/complete",
        json={
            "evidence_text": "Đã soạn xong bài viết ưu đãi tuyển sinh và tạo link VietQR",
            "evidence_type": "note",
        },
        headers=headers,
    )
    assert complete_res.status_code == 200
    assert complete_res.json()["status"] == "completed"

    # 6. Đánh giá tuần (Weekly Review)
    review_res = await client.post(
        f"/roadmaps/{data['roadmap']['id']}/review",
        json={
            "completed_summary": "Đã soạn bài và chuẩn bị kênh tiếp cận",
            "evidence_summary": "Có 3 phụ huynh nhắn tin hỏi lịch học",
            "obstacles_summary": "Cần thêm video lớp học thực tế",
            "decision": "continue",
        },
        headers=headers,
    )
    assert review_res.status_code == 200
    assert review_res.json()["decision"] == "continue"

    # 7. Lấy danh sách bằng chứng (Evidence stream)
    evidence_res = await client.get("/roadmaps/evidence", headers=headers)
    assert evidence_res.status_code == 200
    assert len(evidence_res.json()) >= 1

    # 8. Lấy danh sách reviews
    reviews_res = await client.get("/roadmaps/reviews", headers=headers)
    assert reviews_res.status_code == 200
    assert len(reviews_res.json()) >= 1

    # 9. Lấy lịch sử phiên bản Roadmap (History)
    history_res = await client.get("/roadmaps/history", headers=headers)
    assert history_res.status_code == 200
    assert len(history_res.json()) >= 1

    # 10. Khôi phục phiên bản Roadmap (Restore)
    restore_res = await client.post(
        f"/roadmaps/{data['roadmap']['id']}/restore",
        headers=headers,
    )
    assert restore_res.status_code == 200
    restored_data = restore_res.json()
    assert restored_data["roadmap"]["version"] == 2
    assert "Khôi phục từ v1" in restored_data["roadmap"]["title"]
