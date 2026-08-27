export type Language = "VN" | "EN";

/**
 * Bản tiếng Anh, khoá là **chính câu tiếng Việt** trong mã nguồn.
 *
 * Vì sao khoá là câu tiếng Việt chứ không phải `settings.title`
 * -------------------------------------------------------------
 * Từ điển cũ dùng khoá có dấu chấm và **60 trong 99 khoá đã chết** — màn hình
 * gọi chúng bị xoá từ lâu mà khoá vẫn nằm đó, làm người sửa tin rằng độ phủ cao
 * hơn thực tế. Cùng lúc đó 446 chỗ gọi `t("câu tiếng Việt")` không tra được gì
 * nên trả lại nguyên văn: bấm nút EN thì màn làm việc chính không đổi một chữ.
 *
 * Khoá là câu tiếng Việt sửa cả hai chuyện. Lập trình viên viết tiếng Việt như
 * đang viết, không phải bịa tên khoá. Khoá chết thì
 * `node scripts/i18n-audit.mjs` chỉ ra ngay vì nó so khoá với chỗ gọi thật.
 *
 * Hệ quả có chủ ý: một câu tiếng Việt chỉ có một bản tiếng Anh. Trước đây
 * "Lịch đăng" là `Schedule` ở nav và `Content Calendar` ở tiêu đề — cùng một
 * thứ, hai tên. Gộp lại là dọn.
 *
 * Quy tắc khi thêm chuỗi
 * ----------------------
 * - Viết **cả câu**, đừng chẻ. Chỗ cần chèn giá trị thì dùng `{ô}`:
 *   `t("Còn khoảng {posts} bài trong tháng này", { posts })`. Chẻ câu ra thành
 *   `t("Còn khoảng")` + số + `t("bài")` thì tiếng Anh sai trật tự từ, và người
 *   dịch không thấy được ngữ cảnh.
 * - Thiếu bản dịch **không phải lỗi chạy**: `t()` trả lại tiếng Việt. Một câu
 *   tiếng Việt lọt vào giao diện tiếng Anh thì người đọc vẫn dùng được app.
 * - Thêm/đổi chuỗi xong thì chạy `node scripts/i18n-audit.mjs`.
 */
export const EN: Record<string, string> = {
  "Bài đã duyệt được xếp theo thời gian bạn chọn. Chỉ kênh đang được backend hỗ trợ và đã cấp quyền mới có thể xuất bản.": "Approved posts follow the time you choose. Only backend-supported channels with valid permissions can publish.",
  "Bài đã đăng": "Published Posts",
  "Bài đã đăng theo kênh": "Posts by Channel",
  "Bài đăng theo tuần": "Weekly Posts",
  "Bản nháp": "Drafts",
  "Bản nháp bài viết hiện chỉ hỗ trợ chèn ảnh.": "Post drafts currently only support images.",
  "Báo cáo": "Reports",
  "Bấm nút là bạn đồng ý với ": "By continuing, you agree to Havi's ",
  "Bỏ nhận": "Release",
  "Bộ nhận diện thương hiệu": "Brand Kit",
  "Chào mừng trở lại! Vui lòng nhập thông tin để truy cập.": "Welcome back! Enter your details to access your account.",
  "Chính Sách Bảo Mật": "Privacy Policy",
  "Chưa có bài": "No posts",
  "Chưa có bài đã đăng": "No published posts yet",
  "Chưa có bài đăng Facebook": "No Facebook posts yet",
  "Chưa kết nối": "Not Connected",
  "Cài Havi ra màn hình chính điện thoại": "Add Havi to Home Screen",
  "Cài Đặt Havi Lên Điện Thoại": "Install Havi on Mobile",
  "Cài đặt": "Settings",
  "Các bài viết Fanpage sau khi được bạn duyệt và đăng thành công sẽ xuất hiện tại đây.": "Posts approved and published to your Fanpage will appear here.",
  "Có kết nối hỏng": "Broken connection detected",
  "Còn khoảng {posts} bài trong tháng này": "~{posts} posts remaining this month",
  "Dùng mượt mà 1-chạm, tiện lợi như app tải về máy": "1-Tap instant access, smooth app experience",
  "Email": "Email",
  "Email chưa đúng — kiểm tra lại giúp nhé": "Invalid email — please check again",
  "Email đã đăng ký": "Registered Email Address",
  "Giọng văn của Havi": "Tone of Voice",
  "Gói cước": "Plan & billing",
  "Gửi liên kết khôi phục": "Send Reset Link",
  "Gửi lại mã": "Resend code",
  "Gửi lại mã sau {seconds}s": "Resend code in {seconds}s",
  "Havi đã gửi mã {n} số tới ": "Havi sent a {n}-digit code to ",
  "Havi — quản trị mạng xã hội nhẹ đầu hơn": "Havi — lighter social media operations",
  "Hiện tại": "Current",
  "Hết hạn": "Expired",
  "Hết lượt tạo bài tháng này": "Monthly generation quota reached",
  "Họ và tên": "Full Name",
  "Hội thoại": "Conversations",
  "Hội thoại đã nhận": "Inbox items received",
  "Khi đăng bài thành công, tỷ trọng theo kênh sẽ hiện ở đây.": "Channel distribution will appear when posts are published.",
  "Khôi phục mật khẩu": "Reset Password",
  "Không còn việc nào đang chờ.": "Nothing waiting.",
  "Không có sự cố nào": "No failures",
  "Không rõ nguyên nhân.": "Unknown reason.",
  "Không thể chọn video": "Cannot select video",
  "Kênh kết nối": "Channels",
  "Kết nối": "Connect",
  "Lý do: ": "Reason: ",
  "Lưu & đăng nhập": "Save & Sign In",
  "Lượt tạo bài sẽ mở lại ngày {date}. Bài đã duyệt vẫn đăng đúng lịch bình thường.": "Creation limit resets on {date}. Previously scheduled posts will publish normally.",
  "Lượt tạo bài sẽ mở lại ngày {date}. Havi báo trước để bạn chủ động lên lịch đăng.": "Creation limit resets on {date}. Havi notifies you in advance to plan posts.",
  "Lượt đăng thất bại": "Failed publishes",
  "Lối tắt nội dung": "Content shortcuts",
  "Lần đầu dùng Havi? ": "First time using Havi? ",
  "Lịch sử": "Activity",
  "Lịch đăng": "Publishing schedule",
  "Mật khẩu": "Password",
  "Mật khẩu cần ít nhất {n} ký tự": "Password must be at least {n} characters",
  "Mật khẩu mới": "New Password",
  "Mật khẩu mới cần ít nhất {n} ký tự": "New password must be at least {n} characters",
  "Mật khẩu đã đổi thành công. Bạn có thể đăng nhập lại bằng mật khẩu mới.": "Password changed successfully. You can now log in with your new password.",
  "Mở menu quản trị": "Open admin menu",
  "Mở trên nền tảng ↗": "Open on platform ↗",
  "Ngành nghề": "Industry",
  "Ngắt kết nối": "Disconnect",
  "Nhận thay": "Take over",
  "Nhập email của bạn để nhận liên kết khôi phục.": "Enter your email address to receive a reset link.",
  "Nhập mật khẩu để đăng nhập": "Please enter your password to sign in",
  "Nhập tên tiệm hoặc tên của bạn": "Please enter your name or business name",
  "Nhập đủ {n} số trong email": "Enter all {n} digits sent to your email",
  "Nối lại": "Reconnect",
  "Nội dung": "Content",
  "Nội dung đã duyệt vẫn là quyết định cuối cùng; Havi dùng thông tin này làm nền tảng khi AI sáng tạo nội dung.": "Havi uses brand voice guidelines when generating drafts for your review.",
  "Phản hồi đã gửi": "Replies sent",
  "Quay lại Nội dung": "Back to Content",
  "Quay lại đăng nhập": "Back to login",
  "Quên mật khẩu?": "Forgot password?",
  "Quản lý doanh nghiệp, tài khoản và kết nối kênh": "Manage business profile, account and channel integrations",
  "Quản lý nội dung, lịch đăng và hội thoại đa kênh trong một nơi.": "Manage content, publishing schedules, and channel conversations in one place.",
  "Quản trị": "Administration",
  "Sau": "Next",
  "Theo dõi tình trạng xuất bản và hội thoại": "Track publishing and conversation operations",
  "Thư viện media": "Media library",
  "Thống kê nhanh": "Quick Stats",
  "Thử lại": "Retry",
  "Trước": "Prev",
  "Tuyệt vời! Không có bài viết nào bị lỗi trong kỳ báo cáo này.": "Great! No posts failed during this reporting period.",
  "Tên doanh nghiệp / Cửa hàng": "Business / Store Name",
  "Tên tiệm cần ít nhất 2 ký tự.": "Business name must be at least 2 characters.",
  "Tôi nhận": "Claim",
  "Tạo nội dung": "Create content",
  "Tạo tài khoản Havi": "Create a Havi Account",
  "Tạo tài khoản miễn phí": "Create Free Account",
  "Việc cần làm": "Work queue",
  "Ví dụ: Nguyễn Thu Hương": "e.g., Sarah Jenkins",
  "Ví dụ: thân thiện, gần gũi, ấm áp, xưng hô thân mật, ngắn gọn súc tích...": "e.g., professional yet warm, concise and engaging...",
  "Xử lý": "Handle",
  "chờ": "waited",
  "Ít nhất {n} ký tự": "At least {n} characters",
  "Đang tải báo cáo…": "Loading reports…",
  "Đang tải danh sách việc…": "Loading work queue…",
  "Đang tải lịch…": "Loading calendar…",
  "Đang tạo tài khoản…": "Creating account…",
  "Đang đăng nhập…": "Signing in…",
  "Đang mở…": "Connecting…",
  "Điều Khoản Dịch Vụ": "Terms of Service",
  "Điều hướng chính": "Main navigation",
  "Điều hướng mobile": "Mobile navigation",
  "Đóng menu quản trị": "Close admin menu",
  "Đã có tài khoản?": "Already have an account?",
  "Đã lưu cài đặt giọng thương hiệu thành công.": "Settings updated successfully.",
  "Đã nối": "Connected",
  "Đăng nhập": "Sign in",
  "Đăng nhập Havi": "Sign in to Havi",
  "Đăng xuất": "Sign Out",
  "Đội ngũ": "Team",
  "📘 Bài Viết Fanpage Facebook Đã Đăng Gần Đây": "Recent Published Facebook Posts",
  "🚨 Bài Đăng Gặp Sự Cố": "Failed Posts",
};
