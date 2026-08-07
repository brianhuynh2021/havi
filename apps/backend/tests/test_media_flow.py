"""Test thật cho /media — upload lên MinIO thật, không mock storage.

Cần cả Postgres và MinIO đang chạy (`npm run infra:up` ở root). Object upload
trong test **không** rollback theo transaction DB — object storage không có
transaction — nên mỗi test dùng object key riêng (uuid trong key) để không đụng
nhau, và các object rác này nằm trong bucket dev, không ảnh hưởng gì.
"""

import httpx
from httpx import AsyncClient


async def _onboard(client: AsyncClient, *, email: str) -> dict:
    """Đăng ký → tạo workspace → refresh để JWT mang active_workspace_id."""
    signup = await client.post(
        "/auth/sign-up", json={"name": "Chị Hương", "email": email, "password": "matkhau123"}
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()

    create = await client.post(
        "/workspaces",
        json={"name": "Spa An Nhiên", "industry": "spa"},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    assert create.status_code == 201, create.text

    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    assert refreshed.status_code == 200, refreshed.text
    return refreshed.json()


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


async def _request_ticket(
    client: AsyncClient,
    headers: dict,
    *,
    filename: str = "anh-goi-dau.jpg",
    content_type: str = "image/jpeg",
    type: str = "image",
) -> dict:
    response = await client.post(
        "/media/upload-ticket",
        json={"filename": filename, "content_type": content_type, "type": type},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _upload_to_storage(ticket: dict, *, content: bytes, content_type: str) -> int:
    """POST multipart lên MinIO đúng như client thật sẽ làm. Trả HTTP status."""
    async with httpx.AsyncClient() as storage_client:
        response = await storage_client.post(
            ticket["upload_url"],
            data=ticket["fields"],
            files={"file": ("upload", content, content_type)},
        )
    return response.status_code


async def test_upload_ticket_tao_asset_o_trang_thai_pending(client: AsyncClient):
    token_pair = await _onboard(client, email="m1@havi.vn")
    headers = _headers(token_pair)

    ticket = await _request_ticket(client, headers)
    assert ticket["upload_url"]
    assert ticket["fields"]

    listed = await client.get("/media", headers=headers)
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "pending"
    assert items[0]["uploaded_at"] is None
    assert items[0]["size_bytes"] is None


async def test_upload_that_len_minio_roi_complete_chuyen_sang_raw(client: AsyncClient):
    token_pair = await _onboard(client, email="m2@havi.vn")
    headers = _headers(token_pair)
    ticket = await _request_ticket(client, headers)

    content = b"\xff\xd8\xff\xe0" + b"\x00" * 40  # JPEG magic bytes hợp lệ
    upload_status = await _upload_to_storage(ticket, content=content, content_type="image/jpeg")
    assert upload_status in (200, 204), f"MinIO từ chối upload: {upload_status}"

    completed = await client.post(f"/media/{ticket['asset_id']}/complete", headers=headers)
    assert completed.status_code == 200, completed.text
    body = completed.json()
    assert body["status"] == "raw"
    assert body["size_bytes"] == len(content)
    assert body["uploaded_at"] is not None
    assert body["url"].endswith(body["filename"])


async def test_complete_khi_chua_upload_tra_409(client: AsyncClient):
    token_pair = await _onboard(client, email="m3@havi.vn")
    headers = _headers(token_pair)
    ticket = await _request_ticket(client, headers)

    # Không upload gì — object không tồn tại trên storage.
    response = await client.post(f"/media/{ticket['asset_id']}/complete", headers=headers)
    assert response.status_code == 409


async def test_complete_hai_lan_tra_409(client: AsyncClient):
    token_pair = await _onboard(client, email="m4@havi.vn")
    headers = _headers(token_pair)
    ticket = await _request_ticket(client, headers)
    await _upload_to_storage(
        ticket, content=b"\xff\xd8\xff\xe0" + b"\x00" * 40, content_type="image/jpeg"
    )

    first = await client.post(f"/media/{ticket['asset_id']}/complete", headers=headers)
    assert first.status_code == 200
    second = await client.post(f"/media/{ticket['asset_id']}/complete", headers=headers)
    assert second.status_code == 409


async def test_content_type_khong_ho_tro_tra_415(client: AsyncClient):
    token_pair = await _onboard(client, email="m5@havi.vn")
    headers = _headers(token_pair)

    response = await client.post(
        "/media/upload-ticket",
        json={"filename": "virus.exe", "content_type": "application/x-msdownload", "type": "image"},
        headers=headers,
    )
    assert response.status_code == 415


async def test_content_type_lech_voi_media_type_tra_415(client: AsyncClient):
    """Khai type=image nhưng gửi content_type audio — phải bị chặn."""
    token_pair = await _onboard(client, email="m6@havi.vn")
    response = await client.post(
        "/media/upload-ticket",
        json={"filename": "ghi-am.mp3", "content_type": "audio/mpeg", "type": "image"},
        headers=_headers(token_pair),
    )
    assert response.status_code == 415


async def test_storage_tu_choi_file_vuot_gioi_han_dung_luong(client: AsyncClient):
    """MinIO phải tự chặn bằng content-length-range, không cần API can thiệp."""
    token_pair = await _onboard(client, email="m7@havi.vn")
    headers = _headers(token_pair)
    ticket = await _request_ticket(client, headers)

    oversized = b"\xff\xd8\xff\xe0" + b"x" * (25 * 1024 * 1024)
    upload_status = await _upload_to_storage(
        ticket, content=oversized, content_type="image/jpeg"
    )
    assert upload_status >= 400, "Storage phải từ chối file vượt giới hạn"


async def test_complete_tu_choi_va_xoa_file_khong_dung_dinh_dang(client: AsyncClient):
    """Chốt lỗ hổng: presigned POST KHÔNG kiểm nội dung file.

    S3/MinIO lưu object với `Content-Type` lấy từ field đã ký trong ticket, nên
    client xin ticket `image/jpeg` rồi POST bytes thực thi vẫn được storage nhận
    (204). Bucket media là public-read, nên chặn phải nằm ở `/complete`: kiểm magic
    bytes, không khớp thì xoá object và trả 400.
    """
    token_pair = await _onboard(client, email="m8@havi.vn")
    headers = _headers(token_pair)
    ticket = await _request_ticket(client, headers)

    # MZ = header file thực thi Windows, không phải JPEG.
    upload_status = await _upload_to_storage(
        ticket, content=b"MZ\x90\x00" + b"\x00" * 60, content_type="image/jpeg"
    )
    assert upload_status in (200, 204), "storage vẫn nhận — đúng như mô tả ở trên"

    completed = await client.post(f"/media/{ticket['asset_id']}/complete", headers=headers)
    assert completed.status_code == 400

    # Object phải bị xoá: gọi complete lần nữa thì không còn file trên storage.
    retry = await client.post(f"/media/{ticket['asset_id']}/complete", headers=headers)
    assert retry.status_code == 409, "object rác vẫn còn trong bucket public"


async def test_complete_nhan_dung_png_va_webp(client: AsyncClient):
    """Magic-byte check không được chặn oan các định dạng ảnh hợp lệ khác."""
    token_pair = await _onboard(client, email="m14@havi.vn")
    headers = _headers(token_pair)

    png = await _request_ticket(client, headers, filename="a.png", content_type="image/png")
    await _upload_to_storage(
        ticket=png, content=b"\x89PNG\r\n\x1a\n" + b"\x00" * 40, content_type="image/png"
    )
    assert (
        await client.post(f"/media/{png['asset_id']}/complete", headers=headers)
    ).status_code == 200

    webp = await _request_ticket(client, headers, filename="b.webp", content_type="image/webp")
    await _upload_to_storage(
        ticket=webp,
        content=b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 20,
        content_type="image/webp",
    )
    assert (
        await client.post(f"/media/{webp['asset_id']}/complete", headers=headers)
    ).status_code == 200


async def test_khong_doc_duoc_media_cua_workspace_khac(client: AsyncClient):
    token_a = await _onboard(client, email="m9@havi.vn")
    token_b = await _onboard(client, email="m10@havi.vn")
    ticket_a = await _request_ticket(client, _headers(token_a))

    # B có JWT hợp lệ + workspace riêng, nhưng asset thuộc workspace của A.
    response = await client.post(
        f"/media/{ticket_a['asset_id']}/complete", headers=_headers(token_b)
    )
    assert response.status_code == 404

    listed_b = await client.get("/media", headers=_headers(token_b))
    assert listed_b.json()["items"] == []


async def test_patch_gan_tag_va_doi_status(client: AsyncClient):
    token_pair = await _onboard(client, email="m11@havi.vn")
    headers = _headers(token_pair)
    ticket = await _request_ticket(client, headers)

    response = await client.patch(
        f"/media/{ticket['asset_id']}",
        json={"tags": ["goi-dau", "thao-duoc"], "status": "archived"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["tags"] == ["goi-dau", "thao-duoc"]
    assert response.json()["status"] == "archived"


async def test_list_filter_theo_tag_va_type(client: AsyncClient):
    token_pair = await _onboard(client, email="m12@havi.vn")
    headers = _headers(token_pair)

    image = await _request_ticket(client, headers, filename="a.jpg")
    audio = await _request_ticket(
        client, headers, filename="b.mp3", content_type="audio/mpeg", type="audio"
    )
    await client.patch(
        f"/media/{image['asset_id']}", json={"tags": ["goi-dau"]}, headers=headers
    )

    by_tag = await client.get("/media?tag=goi-dau", headers=headers)
    assert [i["id"] for i in by_tag.json()["items"]] == [image["asset_id"]]

    by_type = await client.get("/media?type=audio", headers=headers)
    assert [i["id"] for i in by_type.json()["items"]] == [audio["asset_id"]]


async def test_chua_co_workspace_thi_bi_chan_409(client: AsyncClient):
    signup = await client.post(
        "/auth/sign-up",
        json={"name": "A", "email": "m13@havi.vn", "password": "matkhau123"},
    )
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    assert (await client.get("/media", headers=headers)).status_code == 409


async def test_khong_co_token_tra_401(client: AsyncClient):
    assert (await client.get("/media")).status_code == 401
