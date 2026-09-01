"""event_log: cho phép DUY NHẤT thao tác ẩn danh hoá theo quyền được xoá

Migration f2a3b4c5d6e7 khoá `event_log` thành append-only tuyệt đối. Đúng cho
audit, nhưng nó chặn luôn một nghĩa vụ **pháp lý** mạnh hơn: quyền được xoá dữ
liệu (GDPR Art. 17, và yêu cầu Data Deletion Callback của Meta). Chính sách của
Havi ở `docs/security/DATA_RETENTION_AND_CONSENT.md` §7 quy định khi xoá
workspace thì `event_log` phải được ẩn danh — `workspace_id` về NULL,
`input_summary`/`output_summary` bị xoá nội dung.

Hai yêu cầu này xung đột thật, không phải do code sai. Cách xử lý ở đây:

- **Xoá thắng bất biến**, vì nghĩa vụ pháp lý cao hơn quy ước nội bộ.
- Nhưng chỉ thắng trong *đúng một* hình dạng UPDATE: đặt `workspace_id = NULL` và
  ghi hằng `'[redacted]'` vào hai cột summary. Mọi cột còn lại (`tokens_*`,
  `duration_ms`, `provider`, `model`, `error`, `created_at`, `row_hash`) phải giữ
  nguyên. Nghĩa là số liệu kế toán và chuỗi hash **không** sửa được qua cửa này —
  đúng thứ mà "chống gian lận kế toán" cần.
- Thao tác này phải khai báo ý định qua `SET havi.erasure = 'on'` trong cùng
  transaction. Một UPDATE vô tình (bug, script chạy quá tay) không có cờ đó nên
  vẫn bị chặn như trước.

Vì sao không dùng một role riêng thay cho cờ session: Havi kết nối Postgres bằng
đúng một user cho cả app, nên phân quyền theo role sẽ đòi thêm một connection
pool thứ hai chỉ để phục vụ đường xoá. Cờ session tường minh đạt cùng mục đích
(phân biệt *ý định*, không phân biệt *ai*) mà không thêm hạ tầng.

Hash chain sau thao tác này sẽ **không còn khớp** với các dòng đã ẩn danh — điều
đó là đúng và có chủ ý: `verify_chain` sẽ chỉ ra "dữ liệu ở đây đã bị sửa", và
lịch sử xoá nằm ở `event_log` dòng `consent.workspace_deleted` để giải thích vì
sao. Một chuỗi vẫn khớp sau khi nội dung đã đổi mới là chuỗi nói dối.

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
"""

from alembic import op

revision = "b4c5d6e7f8a9"
down_revision = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION havi_event_log_immutable() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'UPDATE'
               -- `current_setting(..., true)` → trả NULL thay vì lỗi khi biến chưa
               -- được đặt. Không có `true` thì mọi UPDATE thường ném lỗi "unrecognized
               -- configuration parameter" thay vì thông báo append-only rõ ràng.
               AND COALESCE(current_setting('havi.erasure', true), '') = 'on'
               AND NEW.workspace_id IS NULL
               AND NEW.input_summary = '[redacted]'
               AND NEW.output_summary = '[redacted]'
               -- Mọi cột còn lại phải y nguyên. `IS NOT DISTINCT FROM` chứ không
               -- `=`: các cột này nullable, và `NULL = NULL` trả NULL nên điều
               -- kiện sẽ hỏng âm thầm đúng ở dòng có giá trị NULL.
               AND NEW.id IS NOT DISTINCT FROM OLD.id
               AND NEW.job_id IS NOT DISTINCT FROM OLD.job_id
               AND NEW.content_item_id IS NOT DISTINCT FROM OLD.content_item_id
               AND NEW.job_kind IS NOT DISTINCT FROM OLD.job_kind
               AND NEW.tokens_in IS NOT DISTINCT FROM OLD.tokens_in
               AND NEW.tokens_out IS NOT DISTINCT FROM OLD.tokens_out
               AND NEW.duration_ms IS NOT DISTINCT FROM OLD.duration_ms
               AND NEW.provider IS NOT DISTINCT FROM OLD.provider
               AND NEW.model IS NOT DISTINCT FROM OLD.model
               AND NEW.error IS NOT DISTINCT FROM OLD.error
               AND NEW.created_at IS NOT DISTINCT FROM OLD.created_at
               AND NEW.row_hash IS NOT DISTINCT FROM OLD.row_hash
               AND NEW.prev_hash IS NOT DISTINCT FROM OLD.prev_hash
            THEN
                RETURN NEW;
            END IF;

            RAISE EXCEPTION
                'event_log là bảng append-only: % bị chặn (id=%)',
                TG_OP, COALESCE(OLD.id::text, '?')
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION havi_event_log_immutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'event_log là bảng append-only: % bị chặn (id=%)',
                TG_OP, COALESCE(OLD.id::text, '?')
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
