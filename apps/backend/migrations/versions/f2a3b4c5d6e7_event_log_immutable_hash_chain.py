"""event_log: bất biến ở tầng database + hash chain chống sửa lịch sử

Trước migration này `event_log` là một bảng thường: `UPDATE`/`DELETE` được, nên
nó chứng minh được rất ít. Một audit trail mà người có quyền ghi cũng sửa được
thì trước auditor nó chỉ là "log ứng dụng", không phải chứng từ.

Hai lớp bảo vệ, giải quyết hai mối đe doạ khác nhau:

1. **Trigger chặn UPDATE/DELETE** — chống *lỗi phần mềm* và sai sót vận hành: một
   `session.merge()` vô ý, một script sửa dữ liệu chạy quá tay. Đây là lớp làm
   việc mỗi ngày.

2. **Hash chain (`row_hash`/`prev_hash`)** — chống *người có quyền*: ai có
   SUPERUSER thì `ALTER TABLE ... DISABLE TRIGGER` là xong lớp 1. Nhưng sửa một
   dòng giữa chuỗi thì mọi `row_hash` sau đó không còn khớp, nên việc sửa **để
   lại dấu** dù trigger có bị tắt. Nó không *ngăn* được, nó làm cho việc đó
   không thể che.

Vì sao hash tính trong trigger (PL/pgSQL) chứ không ở Python: nếu tầng app tính
thì một `INSERT` thẳng bằng psql sẽ tạo dòng không có hash, và chuỗi đứt ở đó —
mà chỗ đứt lại chính là chỗ kẻ sửa muốn tạo. Tính trong database nghĩa là *mọi*
đường ghi đều bị buộc vào chuỗi.

Chuỗi theo `workspace_id` (mỗi tenant một chuỗi), không phải một chuỗi toàn cục:
chuỗi toàn cục biến mọi INSERT thành tranh chấp trên cùng một dòng cuối và
serialize toàn bộ ghi log của mọi khách hàng.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
"""

import sqlalchemy as sa
from alembic import op

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgcrypto cho `digest()` — phải có TRƯỚC khi tạo function dùng nó.
    # `IF NOT EXISTS` vì instance có thể đã bật sẵn.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.add_column("event_log", sa.Column("row_hash", sa.String(length=64), nullable=True))
    op.add_column("event_log", sa.Column("prev_hash", sa.String(length=64), nullable=True))

    # Index để tìm dòng cuối của mỗi workspace trong O(log n). Không có nó thì
    # mỗi INSERT quét toàn bảng để lấy prev_hash, và ghi log chậm dần theo lịch sử.
    op.create_index(
        "ix_event_log_chain_tip",
        "event_log",
        ["workspace_id", "created_at", "id"],
    )

    # Hash được tính TRƯỚC khi ghi (BEFORE INSERT) để `row_hash` là một phần của
    # chính dòng đó — tính sau bằng UPDATE thì vi phạm luôn quy tắc bất biến.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION havi_event_log_hash() RETURNS trigger AS $$
        DECLARE
            tip_hash text;
        BEGIN
            -- Dòng cuối của *cùng* workspace. `IS NOT DISTINCT FROM` chứ không
            -- `=`: workspace_id nullable, và `NULL = NULL` trả NULL nên toàn bộ
            -- dòng hệ thống (workspace_id NULL) sẽ lặng lẽ tạo chuỗi rời rạc.
            SELECT row_hash INTO tip_hash
            FROM event_log
            WHERE workspace_id IS NOT DISTINCT FROM NEW.workspace_id
            ORDER BY created_at DESC, id DESC
            LIMIT 1;

            NEW.prev_hash := tip_hash;

            -- Nối bằng ký tự đơn vị U+001F, không phải dấu phẩy hay khoảng trắng:
            -- các trường là văn bản tự do (`input_summary` do người dùng nhập), nên
            -- một dấu phân cách xuất hiện được trong dữ liệu sẽ cho phép dựng hai
            -- dòng khác nhau ra cùng một hash.
            NEW.row_hash := encode(
                digest(
                    concat_ws(
                        chr(31),
                        COALESCE(tip_hash, ''),
                        NEW.id::text,
                        COALESCE(NEW.workspace_id::text, ''),
                        COALESCE(NEW.job_id::text, ''),
                        COALESCE(NEW.content_item_id::text, ''),
                        COALESCE(NEW.request_id, ''),
                        NEW.job_kind,
                        NEW.input_summary,
                        NEW.output_summary,
                        NEW.tokens_in::text,
                        NEW.tokens_out::text,
                        NEW.duration_ms::text,
                        COALESCE(NEW.provider, ''),
                        COALESCE(NEW.model, ''),
                        COALESCE(NEW.error, ''),
                        NEW.created_at::text
                    ),
                    'sha256'
                ),
                'hex'
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER event_log_hash_before_insert
        BEFORE INSERT ON event_log
        FOR EACH ROW EXECUTE FUNCTION havi_event_log_hash();
        """
    )

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

    # BEFORE, không phải AFTER: AFTER chạy sau khi dòng đã bị sửa trong
    # transaction, nên nó chỉ huỷ được bằng cách rollback. BEFORE chặn thẳng.
    op.execute(
        """
        CREATE TRIGGER event_log_block_update
        BEFORE UPDATE ON event_log
        FOR EACH ROW EXECUTE FUNCTION havi_event_log_immutable();
        """
    )
    op.execute(
        """
        CREATE TRIGGER event_log_block_delete
        BEFORE DELETE ON event_log
        FOR EACH ROW EXECUTE FUNCTION havi_event_log_immutable();
        """
    )

    # TRUNCATE không đi qua trigger FOR EACH ROW — nó xoá sạch bảng mà hai trigger
    # trên không thấy gì. Cần trigger cấp statement riêng, nếu không "append-only"
    # có một lối thoát bằng đúng một câu lệnh.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION havi_event_log_no_truncate() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'event_log là bảng append-only: TRUNCATE bị chặn'
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER event_log_block_truncate
        BEFORE TRUNCATE ON event_log
        FOR EACH STATEMENT EXECUTE FUNCTION havi_event_log_no_truncate();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS event_log_block_truncate ON event_log")
    op.execute("DROP TRIGGER IF EXISTS event_log_block_delete ON event_log")
    op.execute("DROP TRIGGER IF EXISTS event_log_block_update ON event_log")
    op.execute("DROP TRIGGER IF EXISTS event_log_hash_before_insert ON event_log")
    op.execute("DROP FUNCTION IF EXISTS havi_event_log_no_truncate()")
    op.execute("DROP FUNCTION IF EXISTS havi_event_log_immutable()")
    op.execute("DROP FUNCTION IF EXISTS havi_event_log_hash()")
    op.drop_index("ix_event_log_chain_tip", table_name="event_log")
    op.drop_column("event_log", "prev_hash")
    op.drop_column("event_log", "row_hash")
