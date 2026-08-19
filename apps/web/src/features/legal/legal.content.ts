/**
 * Nội dung Điều khoản và Chính sách bảo mật.
 *
 * Mọi câu ở đây phải mô tả đúng thứ hệ thống THẬT SỰ làm — đây là cam kết pháp
 * lý với người dùng, không phải copy marketing. Khi đổi cách xử lý dữ liệu
 * (thêm kênh, thêm vendor, đổi nơi lưu) thì sửa file này trong cùng commit.
 *
 * Bám code hiện tại:
 * - `users`: email, tên, mật khẩu băm Argon2id, SĐT tuỳ chọn (+84…)
 * - `media_assets`: ảnh nằm trên object storage, DB chỉ giữ metadata + object_key
 * - `content_items` / `content_item_versions`: bài và lịch sử sửa
 * - `event_log`: token, provider, latency, job_id — không chứa nội dung bài
 * - LLM: Gemini ưu tiên, fallback Anthropic/OpenAI (`provider_router.py`)
 *
 * CHƯA có và KHÔNG được hứa: xoá tài khoản tự phục vụ, xuất dữ liệu, thông báo
 * vi phạm tự động. Những mục đó nói rõ là "liên hệ email" cho tới khi code xong.
 *
 * ROADMAP §4 Việt Nam-first xếp "Consent, quyền xóa dữ liệu, opt-out và chính
 * sách lưu dữ liệu phải phù hợp quy định Việt Nam hiện hành" vào nhóm cần
 * Product/Legal chốt — bản này là bản nháp kỹ thuật, cần luật sư rà trước khi
 * mời khách beta.
 */

export type Section = { heading: string; paragraphs: string[] };

export const LAST_UPDATED = "08/08/2026";

/** Email liên hệ. Đổi ở đây là đổi mọi chỗ hiển thị. */
export const CONTACT_EMAIL = "hotro@havi.vn";

export const termsSections: Section[] = [
  {
    heading: "1. Havi là gì",
    paragraphs: [
      "Havi là nền tảng trợ lý AI Marketing đa kênh giúp hộ kinh doanh, chủ tiệm Spa, Salon, F&B, BĐS và doanh nghiệp vừa và nhỏ tự động hóa sáng tạo nội dung, kịch bản video ngắn và trực chat bắt lead 24/7.",
      "Bạn chỉ cần nạp ảnh hoặc ghi âm giọng nói, Havi viết bài và kịch bản cho từng kênh (Facebook, TikTok 9:16, Google Maps, YouTube Shorts), và bạn luôn là người duyệt trước khi bài được xuất bản.",
    ],
  },
  {
    heading: "2. Tài khoản và Gói dịch vụ",
    paragraphs: [
      "Bạn cần email và mật khẩu để tạo tài khoản. Bạn chịu trách nhiệm giữ bí mật mật khẩu và mọi hoạt động diễn ra dưới tài khoản của mình.",
      "Bạn phải đủ 18 tuổi và có quyền đại diện cho cơ sở kinh doanh mà bạn đăng ký.",
      "Havi cung cấp 7 ngày dùng thử miễn phí đầy đủ tính năng. Sau thời gian dùng thử, bạn có thể chọn nâng cấp Gói Khởi Nghiệp (189.000 đ/tháng) hoặc Gói Chuyên Nghiệp (369.000 đ/tháng) thanh toán tự động qua mã VietQR chuyển khoản ngân hàng. Bạn có quyền hủy gia hạn bất kỳ lúc nào.",
    ],
  },
  {
    heading: "3. Nội dung do AI tạo ra: bạn là người chịu trách nhiệm cuối cùng",
    paragraphs: [
      "Havi sinh bản nháp bằng mô hình ngôn ngữ lớn. AI có thể viết sai thông tin, sai giá, hoặc đưa ra cam kết mà tiệm bạn không thực hiện được. Havi có bộ lọc an toàn, nhưng bộ lọc không thể bắt hết mọi trường hợp.",
      "Vì vậy mọi bài đều dừng ở trạng thái chờ duyệt, và chỉ xuất bản khi bạn bấm duyệt. Khi bạn duyệt một bài, bạn xác nhận đã đọc và chịu trách nhiệm về nội dung đó, kể cả phần do AI viết.",
      "Bạn giữ toàn bộ 100% quyền sở hữu đối với nội dung mình nạp vào và bài đã duyệt. Havi không đòi quyền sở hữu với chúng.",
    ],
  },
  {
    heading: "4. Bạn không được dùng Havi để",
    paragraphs: [
      "Đăng nội dung vi phạm pháp luật Việt Nam, xâm phạm quyền của người khác, hoặc trái điều khoản của nền tảng nơi bài được đăng.",
      "Nạp ảnh khách hàng khi chưa được họ đồng ý. Đây là trách nhiệm của bạn, không phải của Havi.",
      "Giả danh người khác, tạo đánh giá giả, hoặc dùng Havi để spam.",
    ],
  },
  {
    heading: "5. Kết nối với nền tảng khác",
    paragraphs: [
      "Havi chỉ kết nối với Facebook, Google Business, TikTok, YouTube qua API chính thức của họ. Chúng tôi không thu thập dữ liệu bằng cách crawl, và không dùng công cụ tự động vi phạm điều khoản của các nền tảng đó.",
      "Khi bạn nối một kênh, bạn cũng chịu ràng buộc bởi điều khoản của nền tảng đó. Nếu bên thứ ba thay đổi chính sách hoặc khoá quyền truy cập, tính năng liên quan có thể ngưng hoạt động ngoài tầm kiểm soát của Havi.",
    ],
  },
  {
    heading: "6. Giới hạn trách nhiệm và Chính sách thanh toán",
    paragraphs: [
      "Havi cung cấp 7 ngày dùng thử miễn phí đầy đủ tính năng để bạn trải nghiệm thực tế trước khi quyết định nâng cấp. Do chi phí hạ tầng điện toán và mô hình AI phát sinh ngay khi xử lý, mọi gói dịch vụ (gói theo tháng hoặc gói theo năm) sau khi kích hoạt thành công sẽ không áp dụng hoàn tiền hoặc hoàn tiền theo tỷ lệ thời gian chưa sử dụng.",
      "Đối với gói năm, bạn được hưởng mức giá chiết khấu ưu đãi thanh toán một lần và có quyền sử dụng trọn vẹn trong suốt 365 ngày kể từ ngày kích hoạt.",
      "Bạn có toàn quyền không gia hạn tiếp hoặc chuyển đổi gói cho các chu kỳ tiếp theo mà không bị ràng buộc hay bị trừ tiền tự động.",
      "Havi không chịu trách nhiệm cho thiệt hại phát sinh từ nội dung bạn đã duyệt và đăng, từ việc nền tảng bên thứ ba ngưng dịch vụ, hoặc từ việc bạn mất quyền truy cập tài khoản do lộ mật khẩu.",
    ],
  },
  {
    heading: "7. Ngưng sử dụng",
    paragraphs: [
      "Bạn có thể ngưng dùng Havi bất cứ lúc nào. Để xoá tài khoản và dữ liệu, gửi email tới địa chỉ ở cuối trang: chúng tôi xử lý thủ công trong vòng 30 ngày.",
      "Chúng tôi có thể tạm ngưng tài khoản vi phạm điều khoản, và sẽ báo trước qua email trừ trường hợp cần xử lý khẩn cấp.",
    ],
  },
  {
    heading: "8. Thay đổi điều khoản",
    paragraphs: [
      "Khi sửa điều khoản, chúng tôi cập nhật ngày ở đầu trang và thông báo qua email nếu thay đổi ảnh hưởng đáng kể tới quyền lợi của bạn.",
    ],
  },
];

export const privacySections: Section[] = [
  {
    heading: "1. Chúng tôi thu thập gì",
    paragraphs: [
      "Thông tin tài khoản: email, tên bạn nhập khi đăng ký, và mật khẩu ở dạng đã băm bằng thuật toán Argon2id (chúng tôi không lưu và không đọc được mật khẩu gốc của bạn).",
      "Số điện thoại: chỉ khi bạn tự thêm trong phần Cài đặt, và chỉ dùng để gửi thông báo hoặc xác thực. Không bắt buộc, không dùng để đăng nhập.",
      "Thông tin tiệm: tên tiệm, ngành nghề, giọng văn và những câu bạn không muốn dùng trong bài.",
      "Nội dung bạn nạp: ảnh bạn tải lên và ghi chú bạn gõ, cùng các bản nháp Havi sinh ra và lịch sử mọi lần sửa.",
      "Nhật ký kỹ thuật: thời điểm chạy, thời gian xử lý và lượng token mỗi lần gọi AI. Nhật ký này dùng để đo chi phí và tìm lỗi: nó không chứa nội dung bài viết cá nhân của bạn.",
    ],
  },
  {
    heading: "2. Chúng tôi dùng để làm gì",
    paragraphs: [
      "Để vận hành dịch vụ: sinh bản nháp theo đúng giọng tiệm bạn, xếp bài lên lịch, và hiển thị lịch sử sửa.",
      "Để giữ tài khoản an toàn: phát hiện đăng nhập bất thường và chặn lạm dụng.",
      "Để cải thiện Havi: xem nhật ký kỹ thuật và số liệu tổng hợp. Chúng tôi không đọc nội dung bài của bạn để phục vụ mục đích thương mại ngoài luồng.",
      "Chúng tôi cam kết 100% không bán dữ liệu của bạn, và không dùng nội dung của bạn để quảng cáo cho bên thứ ba.",
    ],
  },
  {
    heading: "3. Dữ liệu đi tới đâu",
    paragraphs: [
      "Để sinh bản nháp, Havi gửi thông tin tiệm và dữ liệu thô bạn nạp tới nhà cung cấp mô hình AI: ưu tiên Google Gemini, và Anthropic hoặc OpenAI khi Gemini gặp sự cố. Các nhà cung cấp này xử lý dữ liệu theo điều khoản bảo mật dành cho khách hàng doanh nghiệp của họ.",
      "Khi bạn duyệt một bài, nội dung đó được gửi tới nền tảng bạn đã nối (Facebook, Google Maps, TikTok, YouTube) qua API chính thức.",
      "Ngoài hai trường hợp trên, chúng tôi chỉ chia sẻ dữ liệu khi có yêu cầu hợp pháp từ cơ quan nhà nước có thẩm quyền.",
    ],
  },
  {
    heading: "4. Dữ liệu được giữ bao lâu",
    paragraphs: [
      "Dữ liệu tài khoản và nội dung được giữ trong suốt thời gian bạn còn sử dụng Havi.",
      "Khi bạn gửi yêu cầu qua email để xoá tài khoản, chúng tôi xử lý thủ công trong vòng 30 ngày để xóa toàn bộ dữ liệu cá nhân và nội dung liên kết. Nhật ký kỹ thuật ẩn danh không gắn với danh tính bạn có thể được giữ lại để phân tích chi phí.",
      "Bản sao lưu được xoay vòng và sẽ hết hạn theo chu kỳ sao lưu sau khi dữ liệu chính đã bị xoá.",
    ],
  },
  {
    heading: "5. Chúng tôi bảo vệ dữ liệu thế nào",
    paragraphs: [
      "Mật khẩu được băm bằng thuật toán Argon2id: kể cả quản trị viên cũng không đọc được mật khẩu gốc.",
      "Toàn bộ OAuth Access Token của các kênh mạng xã hội được mã hóa bằng khóa AES-128 Fernet.",
      "Dữ liệu mỗi tiệm được tách riêng độc lập ở tầng truy vấn cơ sở dữ liệu (Multi-tenant data isolation) để tiệm này không bao giờ đọc được dữ liệu của tiệm khác.",
      "Ảnh bạn tải lên đi thẳng lên kho lưu trữ qua đường truyền HTTPS mã hoá; hệ thống kiểm tra định dạng thật của file trước khi nhận.",
      "Nhật ký hệ thống không ghi mật khẩu, mã xác thực hay token đăng nhập.",
      "Mặc dù áp dụng các tiêu chuẩn bảo mật khắt khe, trên thực tế không hệ thống nào an toàn tuyệt đối. Nếu xảy ra sự cố ảnh hưởng tới dữ liệu của bạn, chúng tôi sẽ thông báo ngay qua email.",
    ],
  },
  {
    heading: "6. Quyền của bạn",
    paragraphs: [
      "Theo pháp luật Việt Nam về bảo vệ dữ liệu cá nhân (Nghị định 13/2023/NĐ-CP), bạn có đầy đủ các quyền: quyền biết dữ liệu nào của mình đang được xử lý, yêu cầu sửa dữ liệu sai, yêu cầu xoá dữ liệu, và rút lại sự đồng ý.",
      "Bạn sửa được thông tin tiệm và giọng văn ngay trong ứng dụng. Với các yêu cầu còn lại: xem toàn bộ dữ liệu, xuất dữ liệu, hoặc xoá tài khoản: hiện bạn gửi email cho chúng tôi và chúng tôi xử lý thủ công trong vòng 30 ngày.",
      "Bạn cũng có quyền khiếu nại lên cơ quan nhà nước có thẩm quyền nếu cho rằng dữ liệu của mình bị xử lý sai quy định.",
    ],
  },
  {
    heading: "7. Ảnh có mặt khách hàng",
    paragraphs: [
      "Nếu bạn nạp ảnh có hình khách hàng, bạn phải được họ đồng ý trước. Havi không thay bạn xin phép, và không kiểm tra được điều này.",
      "Khách hàng trong ảnh có quyền yêu cầu gỡ hình của họ. Khi nhận yêu cầu như vậy, chúng tôi sẽ liên hệ với bạn để xử lý kịp thời.",
    ],
  },
  {
    heading: "8. Cookie và theo dõi",
    paragraphs: [
      "Havi lưu phiên đăng nhập trên trình duyệt của bạn để bạn không phải đăng nhập lại mỗi lần vào. Chúng tôi không dùng cookie quảng cáo và không theo dõi bạn trên các trang web khác.",
    ],
  },
];
