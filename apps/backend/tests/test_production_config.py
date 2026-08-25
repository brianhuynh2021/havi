import pytest
from pydantic import ValidationError

from core.config import Settings


def test_production_rejects_defaults_and_missing_real_providers():
    with pytest.raises(ValidationError, match="Production configuration"):
        Settings(
            env="production",
            use_mock_llm=False,
            use_fake_publisher=False,
            disable_rate_limit=False,
                email_provider="smtp",
            email_from="no-reply@havi.vn",
            smtp_host="smtp.havi.vn",
        )
