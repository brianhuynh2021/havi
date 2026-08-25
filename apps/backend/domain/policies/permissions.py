"""Vai trò nào làm được việc gì. Domain policy thuần — không I/O, không HTTP.

Vì sao phải cưỡng chế chứ không chỉ hiển thị: quy trình **soạn → duyệt → đăng**
chỉ có nghĩa khi hai vai đó tách rời được. Nếu ai cũng duyệt được thì bước duyệt
chỉ là một cú bấm thêm của chính người vừa soạn — và toàn bộ lời hứa "không gì
lên kênh mà chưa qua mắt người khác" trở thành trang trí.

Bảng nằm ở một chỗ, thay vì rải `if role == ...` trong từng router: thêm một vai
mới hay đổi quyền một vai là sửa đúng một nơi, và mỗi cú sửa đều thành một lỗi
test chứ không phải một lỗ hổng im lặng.
"""

from core.enums import WorkspaceRole


class Permission:
    """Việc làm được, đặt tên theo *hành động*, không theo tên màn hình.

    Màn hình đổi tên liên tục; hành động thì không. `APPROVE_CONTENT` vẫn đúng
    dù nút nằm ở "Nội dung", "Đăng bài" hay "Lịch đăng".
    """

    #: Soạn nháp, sửa nháp, tải media lên.
    DRAFT_CONTENT = "draft_content"
    #: Bấm duyệt để nội dung được xếp lịch và lên kênh.
    APPROVE_CONTENT = "approve_content"
    #: Trả lời tin nhắn và bình luận của khách.
    REPLY_CONVERSATION = "reply_conversation"
    #: Nối/ngắt kênh social của workspace.
    MANAGE_CONNECTIONS = "manage_connections"
    #: Mời, đổi vai, gỡ thành viên.
    MANAGE_MEMBERS = "manage_members"
    #: Xem lịch sử hoạt động của cả workspace.
    VIEW_AUDIT_LOG = "view_audit_log"


#: Vai → tập quyền. Không kế thừa lồng nhau: một bảng đọc thẳng thì nhìn phát
#: biết ai làm được gì, còn kế thừa thì phải lần ngược nhiều tầng mới trả lời
#: được câu "rốt cuộc Sales có duyệt bài được không?".
ROLE_PERMISSIONS: dict[WorkspaceRole, frozenset[str]] = {
    WorkspaceRole.OWNER: frozenset(
        {
            Permission.DRAFT_CONTENT,
            Permission.APPROVE_CONTENT,
            Permission.REPLY_CONVERSATION,
            Permission.MANAGE_CONNECTIONS,
            Permission.MANAGE_MEMBERS,
            Permission.VIEW_AUDIT_LOG,
        }
    ),
    # Người soạn KHÔNG tự duyệt bài mình viết. Đây là toàn bộ lý do vai này tồn
    # tại tách khỏi Reviewer.
    WorkspaceRole.MARKETER: frozenset(
        {Permission.DRAFT_CONTENT, Permission.REPLY_CONVERSATION}
    ),
    # Người duyệt cũng soạn được — thực tế ở tiệm nhỏ một người kiêm cả hai, và
    # chặn điều đó chỉ khiến họ dùng chung một tài khoản Owner, tệ hơn hẳn.
    WorkspaceRole.REVIEWER: frozenset(
        {
            Permission.DRAFT_CONTENT,
            Permission.APPROVE_CONTENT,
            Permission.REPLY_CONVERSATION,
            Permission.VIEW_AUDIT_LOG,
        }
    ),
    # Trực hội thoại: chỉ chạm tới khách, không chạm tới nội dung sẽ lên kênh.
    WorkspaceRole.SALES: frozenset({Permission.REPLY_CONVERSATION}),
}


def can(role: WorkspaceRole | None, permission: str) -> bool:
    """`None` = không phải thành viên → không quyền gì. Fail-closed."""
    if role is None:
        return False
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def roles_with(permission: str) -> list[WorkspaceRole]:
    """Vai nào có quyền này — để thông báo lỗi nói được ai làm giúp được."""
    return [role for role, perms in ROLE_PERMISSIONS.items() if permission in perms]
