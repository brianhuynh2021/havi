"""Rate limit theo endpoint — con số ở đúng một chỗ.

Ba nhóm cần chặn, mỗi nhóm một lý do khác nhau:

1. **Auth** — chặn brute force mật khẩu và mã đặt lại. Đây là bảo mật: không có
   giới hạn thì một script thử vài nghìn mật khẩu một phút.
2. **Upload** — chặn ai đó đốt dung lượng object storage bằng cách xin ticket
   liên tục.
3. **Content generation** — chặn tiền LLM. Quota tháng đã chặn tổng, nhưng nó
   không chặn được việc đốt hết quota trong 5 phút; rate limit chặn *nhịp*.

Giới hạn đặt rộng hơn nhịp dùng thật khá nhiều: chặn oan một chủ tiệm đang cần
đăng bài tệ hơn để lọt vài request thừa. Đây là số cần đo lại sau pilot.
"""

from adapters.ratelimit import RateLimitRule

#: Đăng nhập / đăng ký: theo IP. 10 lượt / 5 phút.
#:
#: Theo IP chứ không theo email: kẻ brute force đổi email mỗi lượt thì giới hạn
#: theo email chặn được đúng số 0. Đánh đổi là nhiều người sau cùng một NAT
#: (quán net, văn phòng) chia nhau hạn mức — nên để rộng 10 lượt.
AUTH_LOGIN = RateLimitRule(limit=10, window_seconds=300)

#: Xin mã đặt lại mật khẩu: theo IP, chặt hơn login vì mỗi lượt sẽ gửi một email
#: thật (tốn tiền, và spam hộp thư người khác nếu bị lợi dụng).
AUTH_PASSWORD_RESET = RateLimitRule(limit=5, window_seconds=900)

#: Xin upload ticket: theo workspace. 60 lượt / 5 phút — một lần nạp liệu vài ảnh
#: là bình thường, nhưng 60 thì đang có gì đó sai.
MEDIA_UPLOAD_TICKET = RateLimitRule(limit=60, window_seconds=300)

#: Tạo content job: theo workspace. 10 lượt / 5 phút.
#:
#: Mỗi job là một lần gọi LLM tốn tiền thật. `Idempotency-Key` đã chặn
#: double-submit, và quota tháng chặn tổng — cái này chặn *nhịp*, để một script
#: lỗi (hoặc người bấm liên tục) không đốt hết quota tháng trong vài phút.
CONTENT_JOB = RateLimitRule(limit=10, window_seconds=300)
