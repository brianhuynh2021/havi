"""Cấu hình backend. Mọi secret chỉ tồn tại ở đây, không bao giờ đi ra frontend."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HAVI_",
        env_file=(".env", "apps/backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        # Không để pydantic-settings tự parse field kiểu list/dict thành JSON.
        # Mặc định nó parse TRƯỚC validator, nên `HAVI_CORS_ORIGINS=a,b` (đúng
        # như .env.example ghi) ném SettingsError thay vì chạy `_split_origins`
        # bên dưới — backend không khởi động nổi với file .env mẫu.
        enable_decoding=False,
    )

    env: Literal["local", "staging", "production"] = "local"
    debug: bool = True

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://0.0.0.0:3000",
        ]
    )

    database_url: str = "postgresql+psycopg://havi:havi@localhost:5432/havi"
    redis_url: str = "redis://localhost:6379/0"

    media_bucket: str = "havi-media"
    media_public_url: str = "http://localhost:9000/havi-media"
    # S3-compatible endpoint (MinIO ở local, S3/R2/Spaces ở production).
    media_endpoint_url: str = "http://localhost:9000"
    media_access_key: str = "minioadmin"
    media_secret_key: str = "minioadmin"
    media_region: str = "us-east-1"
    media_upload_ttl_seconds: int = 900
    # Chặn ở tầng storage bằng presigned POST condition, không chỉ tin client.
    media_max_upload_bytes: int = 25 * 1024 * 1024

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 60
    refresh_token_ttl_days: int = 30
    otp_ttl_seconds: int = 300
    otp_resend_cooldown_seconds: int = 30
    otp_max_attempts: int = 5

    # Local/debug returns `debug_code` for password reset. Staging/production must
    # configure a real provider; otherwise the reset flow pretends to send email
    # while the user never receives anything.
    email_provider: Literal["debug", "smtp"] = "debug"
    email_from: str = ""
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_timeout_seconds: int = 10

    token_encryption_key: str = "DGS23enMkRy4RNlP8jhrCCOGqz4mVV76lvwWLjn9wq4="

    # Dùng MockProvider thay vì gọi LLM thật. Mặc định bật ở local để chạy tay
    # không tốn tiền; `_force_real_llm_outside_local` bên dưới chặn nó ở
    # staging/production, nơi bắt buộc phải verify bằng model thật.
    use_mock_llm: bool = True

    # Dùng FakePublisher thay vì gọi Graph API thật. Mặc định bật ở local để
    # chạy tay không đăng nhầm lên Trang thật; `_force_real_publisher_outside_local`
    # bên dưới chặn nó ở staging/production.
    use_fake_publisher: bool = True

    # Tắt rate limit (dùng NullRateLimiter). Chỉ cho test — validator bên dưới
    # chặn ở staging/production, cùng khuôn với hai cờ trên: rate limit tắt âm
    # thầm ở production là mở cửa cho brute force mà không có dấu hiệu gì.
    disable_rate_limit: bool = False

    # Multi-provider LLM (SYSTEM_ARCHITECTURE.md §5.1) — Gemini ưu tiên, hai
    # provider còn lại là fallback khi Gemini lỗi/quota/output không đạt.
    # Provider thiếu key sẽ bị router bỏ qua, không gọi rồi lỗi.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    openai_api_key: str = ""
    openai_model: str = "gpt-5"

    facebook_client_id: str = ""
    facebook_client_secret: str = ""
    # Redirect URI phải khớp TỪNG KÝ TỰ với giá trị khai trong Facebook App
    # Settings, kể cả dấu `/` cuối. Lệch một ký tự thì Facebook trả
    # `redirect_uri_isn't an absolute URI` ở bước đổi code — nên đọc từ config
    # chứ không dựng từ request host: sau reverse proxy, host thấy được là host
    # nội bộ, không phải domain người dùng bấm vào.
    facebook_redirect_uri: str = "http://localhost:8000/connections/facebook/callback"
    # ID của một "Configuration" trong Facebook Login for Business. Loại app này
    # khai quyền sẵn trong configuration thay vì nhận `scope` trên URL — gửi
    # `scope` là Facebook trả `Invalid Scopes` ở callback. Để trống nếu app dùng
    # Facebook Login thường (khi đó adapter gửi `scope` như cũ).
    facebook_config_id: str = ""
    # Gốc URL của apps/web — callback OAuth ghép đường về vào đây. Callback là
    # điều hướng của trình duyệt (không phải fetch), nên phải trả redirect về app
    # chứ không trả JSON.
    #
    # Biến riêng chứ không lấy `cors_origins[0]`: hai thứ tình cờ giống nhau ở
    # local nhưng khác hẳn khi lên production (CORS có thể có nhiều origin, và
    # thứ tự trong danh sách không phải hợp đồng gì cả). Dùng phần tử đầu của
    # CORS làm base URL là loại lỗi chỉ lộ ra sau khi deploy.
    web_base_url: str = "http://localhost:3000"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_business_redirect_uri: str = "http://localhost:8000/connections/google_business/callback"
    youtube_redirect_uri: str = "http://localhost:8000/connections/youtube/callback"
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_redirect_uri: str = "http://localhost:8000/connections/tiktok/callback"
    # Chuỗi tự đặt, khai cùng lúc ở Meta App Dashboard và ở đây. Meta gọi
    # `GET /webhooks/meta` một lần với chuỗi này để xác nhận endpoint là của
    # Havi. Để trống thì endpoint webhook trả 503 — chưa cấu hình thì không nhận
    # dữ liệu, thay vì nhận bừa.
    meta_webhook_verify_token: str = ""
    zalo_client_id: str = ""
    zalo_client_secret: str = ""
    zalo_redirect_uri: str = "http://localhost:8000/connections/zalo_oa/callback"
    # Mã Zalo cấp để xác minh quyền sở hữu domain. Nằm trong config chứ không
    # hardcode trong `api/main.py`: mỗi môi trường một domain nên một mã khác
    # nhau, và mã trong source là thứ không xoay được khi cần đổi.
    zalo_site_verification: str = ""
    # Phần đuôi của file xác minh Zalo yêu cầu đặt ở gốc domain, ví dụ
    # `zalo_verifierAbC123.html` thì đây là `AbC123.html`.
    zalo_verifier_suffix: str = ""
    # Telegram Bot Hot Lead Radar Alerts
    telegram_bot_token: str = ""
    telegram_default_chat_id: str = ""
    # Cổng thanh toán tự động VietQR & PayOS
    payos_client_id: str = ""
    payos_api_key: str = ""
    payos_checksum_key: str = ""
    vietqr_bank_id: str = "MB"
    vietqr_account_no: str = "0987654321"
    vietqr_account_name: str = "TRUNG TAM CONG NGHE NHAT MINH"
    payment_webhook_secret: str = "havi_payment_secret_2026"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _force_real_llm_outside_local(self) -> "Settings":
        """Mock LLM chỉ được sống ở local.

        Ném lỗi lúc khởi động thay vì âm thầm tắt mock: staging/production mà
        lỡ để `HAVI_USE_MOCK_LLM=true` thì mọi bản nháp là văn mẫu — chủ tiệm
        đăng lên Facebook thật mà tưởng AI viết. Sai kiểu đó phải chặn ngay ở
        deploy, không phải phát hiện sau khi bài đã lên mạng.
        """
        if self.use_mock_llm and self.env != "local":
            raise ValueError(
                f"HAVI_USE_MOCK_LLM=true không được phép khi HAVI_ENV={self.env}. "
                "Mock LLM chỉ dùng ở local; staging/production phải gọi model thật."
            )
        return self

    @model_validator(mode="after")
    def _force_real_publisher_outside_local(self) -> "Settings":
        """FakePublisher chỉ được sống ở local.

        Sai kiểu này im lặng và tệ hơn mock LLM: mọi bài đều báo "đã đăng",
        dashboard xanh, chủ tiệm tin là Facebook đã có bài — trong khi Trang
        trống trơn. Phát hiện ra thì đã mất mấy ngày nội dung. Chặn ở deploy.
        """
        if self.use_fake_publisher and self.env != "local":
            raise ValueError(
                f"HAVI_USE_FAKE_PUBLISHER=true không được phép khi HAVI_ENV={self.env}. "
                "Fake publisher chỉ dùng ở local; staging/production phải đăng thật."
            )
        return self

    @model_validator(mode="after")
    def _force_rate_limit_outside_local(self) -> "Settings":
        """Rate limit chỉ được tắt ở local.

        Sai kiểu im lặng nhất trong ba cờ này: không có gì hiện ra, app chạy y
        như thường, chỉ là brute force mật khẩu không còn bị chặn và một script
        lỗi đốt hết quota LLM trong vài phút. Không ai phát hiện cho tới khi có
        sự cố. Chặn ở deploy.
        """
        if self.disable_rate_limit and self.env != "local":
            raise ValueError(
                f"HAVI_DISABLE_RATE_LIMIT=true không được phép khi HAVI_ENV={self.env}. "
                "Tắt rate limit chỉ dùng cho test ở local."
            )
        return self

    @model_validator(mode="after")
    def _force_real_email_outside_local(self) -> "Settings":
        """Password reset email must be real outside local development."""
        if self.env == "local":
            return self
        if self.email_provider == "debug":
            raise ValueError(
                f"HAVI_EMAIL_PROVIDER=debug không được phép khi HAVI_ENV={self.env}. "
                "Staging/production phải cấu hình provider email thật."
            )
        if self.email_provider == "smtp" and (not self.email_from or not self.smtp_host):
            raise ValueError("HAVI_EMAIL_PROVIDER=smtp cần HAVI_EMAIL_FROM và HAVI_SMTP_HOST.")
        return self

    @property
    def expose_debug_codes(self) -> bool:
        """Only local debug mode can reveal OTPs in API responses."""
        return self.env == "local" and self.debug


@lru_cache
def get_settings() -> Settings:
    return Settings()
