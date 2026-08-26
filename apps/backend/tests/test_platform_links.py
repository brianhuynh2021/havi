"""Link ra nền tảng — và chỗ nào cố ý KHÔNG có link.

Nguyên tắc được khoá ở đây: thà không có nút hơn là nút dẫn sai. Một nút "Mở trên
Facebook" dẫn tới trang chủ tệ hơn không có nút — người dùng bấm vài lần rồi học
được rằng bấm cũng chẳng để làm gì, và sau đó bỏ qua cả lúc nó dẫn đúng.
"""

from core.enums import InboxItemType, Platform
from domain.policies import platform_links


class TestInboxItemUrl:
    def test_binh_luan_facebook_co_link(self):
        url = platform_links.inbox_item_url(
            platform=Platform.FACEBOOK,
            item_type=InboxItemType.COMMENT,
            external_message_id="123_456",
        )
        assert url == "https://www.facebook.com/123_456"

    def test_danh_gia_facebook_co_link(self):
        assert (
            platform_links.inbox_item_url(
                platform=Platform.FACEBOOK,
                item_type=InboxItemType.REVIEW,
                external_message_id="789_012",
            )
            is not None
        )

    def test_tin_nhan_messenger_KHONG_co_link(self):
        """Cố ý. Hội thoại Messenger của một Trang không có URL công khai dựng
        được từ PSID; muốn có thì phải đọc thêm thread id qua Graph API. Đoán một
        URL là đúng loại sai mà module này tồn tại để tránh."""
        assert (
            platform_links.inbox_item_url(
                platform=Platform.FACEBOOK,
                item_type=InboxItemType.MESSAGE,
                external_message_id="psid-abc",
            )
            is None
        )

    def test_khong_co_external_id_thi_khong_co_link(self):
        assert (
            platform_links.inbox_item_url(
                platform=Platform.FACEBOOK,
                item_type=InboxItemType.COMMENT,
                external_message_id=None,
            )
            is None
        )

    def test_kenh_chua_bat_thi_khong_co_link(self):
        """TikTok và YouTube chưa chạy. Trả link cho kênh chưa bật là hứa một
        thứ chưa tồn tại."""
        for platform in (Platform.TIKTOK, Platform.YOUTUBE, Platform.ZALO_OA):
            assert (
                platform_links.inbox_item_url(
                    platform=platform,
                    item_type=InboxItemType.COMMENT,
                    external_message_id="abc",
                )
                is None
            )

    def test_nhan_ca_enum_va_chuoi(self):
        """Giá trị đọc từ database về có thể là chuỗi thô."""
        assert platform_links.inbox_item_url(
            platform="facebook", item_type="comment", external_message_id="1_2"
        ) == platform_links.inbox_item_url(
            platform=Platform.FACEBOOK,
            item_type=InboxItemType.COMMENT,
            external_message_id="1_2",
        )


class TestPublishedPostUrl:
    def test_bai_facebook_da_dang_co_link(self):
        """`external_post_id` cũng chính là bằng chứng bài đã lên thật — Havi chỉ
        ghi `published` khi nền tảng trả về id này."""
        assert (
            platform_links.published_post_url(
                platform=Platform.FACEBOOK, external_post_id="page_1_post_2"
            )
            == "https://www.facebook.com/page_1_post_2"
        )

    def test_chua_co_id_thi_khong_co_link(self):
        assert (
            platform_links.published_post_url(
                platform=Platform.FACEBOOK, external_post_id=None
            )
            is None
        )
