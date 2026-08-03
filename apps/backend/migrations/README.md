# Migrations

Alembic migrations của Havi backend. Chưa khởi tạo — DB schema sẽ được thêm khi bắt đầu
implement domain thật.

Khi bắt đầu:

```bash
uv sync --extra db
uv run alembic init -t async .
```

Quy tắc:

- Backend là chủ sở hữu duy nhất của database. Frontend không bao giờ kết nối trực tiếp.
- Mọi bảng nghiệp vụ đều có `workspace_id` và mọi query đều scope theo nó — không cho
  leak chéo tenant.
- Migration được deploy tách riêng khỏi 3 process (api / worker / scheduler), xem
  `docs/architecture/REPOSITORY_STRATEGY.md` §2.
