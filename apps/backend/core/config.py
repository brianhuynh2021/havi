"""Cấu hình backend. Mọi secret chỉ tồn tại ở đây, không bao giờ đi ra frontend."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HAVI_",
        env_file=".env",
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

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

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

    token_encryption_key: str = ""

    # Dùng MockProvider thay vì gọi LLM thật. Mặc định bật ở local để chạy tay
    # không tốn tiền; `_force_real_llm_outside_local` bên dưới chặn nó ở
    # staging/production, nơi bắt buộc phải verify bằng model thật.
    use_mock_llm: bool = True

    # Multi-provider LLM (SYSTEM_ARCHITECTURE.md §5.1) — Gemini ưu tiên, hai
    # provider còn lại là fallback khi Gemini lỗi/quota/output không đạt.
    # Provider thiếu key sẽ bị router bỏ qua, không gọi rồi lỗi.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
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
    # Người dùng được đưa về đây sau callback. Callback là điều hướng của trình
    # duyệt (không phải fetch), nên nó phải trả redirect về app chứ không trả JSON.
    oauth_success_redirect_url: str = "http://localhost:3000/cai-dat/ket-noi"
    google_client_id: str = ""
    google_client_secret: str = ""
    zalo_client_id: str = ""
    zalo_client_secret: str = ""

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
