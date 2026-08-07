# Migrations

Alembic (async template), khởi tạo qua `docker-compose.yml` ở root + local stack.

## Chạy local stack trước

```bash
docker compose up -d          # postgres, redis, minio (từ root repo)
```

## Tạo/chạy migration

```bash
cd apps/backend
uv sync --extra db
uv run alembic revision --autogenerate -m "mô tả ngắn"
uv run alembic upgrade head
```

`migrations/env.py` đọc connection string trực tiếp từ `core.config.Settings`
(`HAVI_DATABASE_URL`) — không set `sqlalchemy.url` trong `alembic.ini`, tránh hai
nguồn sự thật.

`target_metadata` trong `env.py` đang là `None` vì chưa có domain model nào. Khi
bắt đầu implement persistence thật (Tuần 4, xem `docs/product/ROADMAP.md`), trỏ
nó vào `Base.metadata` của SQLAlchemy models trong `domain/models/` để
`--autogenerate` hoạt động.

## Quy tắc

- Backend là chủ sở hữu duy nhất của database. Frontend không bao giờ kết nối trực tiếp.
- Mọi bảng nghiệp vụ đều có `workspace_id` và mọi query đều scope theo nó — không cho
  leak chéo tenant.
- Migration được deploy tách riêng khỏi 3 process (api / worker / scheduler), xem
  `docs/architecture/REPOSITORY_STRATEGY.md` §2.
- Mỗi thay đổi schema đi qua migration; không sửa production database thủ công.
