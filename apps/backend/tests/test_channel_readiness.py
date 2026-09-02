"""Kiểm tra sự nhất quán giữa LIVE_CHANNELS và CHANNEL_REGISTRY.

Theo COMMERCIAL_READINESS_PROMPT §1.2:
Mọi kênh nằm trong LIVE_CHANNELS bắt buộc phải thoả mãn đầy đủ các trường trong ChannelReadiness.
Nếu thiếu một trường hoặc bật kênh khi chưa đủ điều kiện, CI bắt buộc phải đỏ.
"""

from domain.policies.channel_capabilities import LIVE_CHANNELS
from domain.policies.channel_readiness import CHANNEL_REGISTRY


def test_every_live_channel_has_complete_readiness():
    for channel in LIVE_CHANNELS:
        assert channel in CHANNEL_REGISTRY, f"Kênh {channel} trong LIVE_CHANNELS chưa được khai trong CHANNEL_REGISTRY"
        readiness = CHANNEL_REGISTRY[channel]
        assert readiness.provider_audit_passed, f"Kênh {channel} chưa pass provider audit"
        assert readiness.publish_verified_live_on is not None, f"Kênh {channel} chưa có ngày publish verified live"
        assert readiness.reconciliation_implemented, f"Kênh {channel} chưa cài đặt reconciliation"
        assert readiness.conformance_suite_passing, f"Kênh {channel} chưa pass conformance suite"
        assert readiness.proactive_health_check, f"Kênh {channel} chưa có proactive health check"
        assert readiness.pricing_page_updated, f"Kênh {channel} chưa cập nhật trang giá"
        assert readiness.is_live_ready, f"Kênh {channel} is_live_ready phải là True"


def test_non_live_channels_are_not_falsely_marked_ready():
    for channel, readiness in CHANNEL_REGISTRY.items():
        if channel not in LIVE_CHANNELS:
            assert not readiness.is_live_ready, f"Kênh {channel} chưa thuộc LIVE_CHANNELS nhưng lại được đánh dấu live_ready"
