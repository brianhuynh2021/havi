"""Sổ đăng ký sẵn sàng kênh — Single source of truth cho điều kiện kênh được coi là LIVE.

Theo COMMERCIAL_READINESS_PROMPT §1.2:
Một kênh chỉ được coi là LIVE và bán được khi nó thoả mãn đầy đủ 6 điều kiện kiểm chứng.
"""

from dataclasses import dataclass
from datetime import date

from core.enums import Channel


@dataclass(frozen=True)
class ChannelReadiness:
    provider_audit_passed: bool  # Meta App Review / TikTok audit / Google verification
    publish_verified_live_on: date | None  # ngày đăng thật, có external id, ghi trong ROADMAP
    reconciliation_implemented: bool
    conformance_suite_passing: bool
    proactive_health_check: bool  # token/quyền được kiểm chủ động, không chỉ khi đăng lỗi
    pricing_page_updated: bool

    @property
    def is_live_ready(self) -> bool:
        return (
            self.provider_audit_passed
            and self.publish_verified_live_on is not None
            and self.reconciliation_implemented
            and self.conformance_suite_passing
            and self.proactive_health_check
            and self.pricing_page_updated
        )


#: Sổ đăng ký tình trạng sẵn sàng của từng kênh
CHANNEL_REGISTRY: dict[Channel, ChannelReadiness] = {
    Channel.FACEBOOK_PAGE: ChannelReadiness(
        provider_audit_passed=True,
        publish_verified_live_on=date(2026, 8, 20),
        reconciliation_implemented=True,
        conformance_suite_passing=True,
        proactive_health_check=True,
        pricing_page_updated=True,
    ),
    Channel.REELS: ChannelReadiness(
        provider_audit_passed=True,
        publish_verified_live_on=date(2026, 8, 20),
        reconciliation_implemented=True,
        conformance_suite_passing=True,
        proactive_health_check=True,
        pricing_page_updated=True,
    ),
    Channel.TIKTOK: ChannelReadiness(
        provider_audit_passed=False,
        publish_verified_live_on=None,
        reconciliation_implemented=True,
        conformance_suite_passing=True,
        proactive_health_check=True,
        pricing_page_updated=False,
    ),
    Channel.YOUTUBE: ChannelReadiness(
        provider_audit_passed=False,
        publish_verified_live_on=None,
        reconciliation_implemented=True,
        conformance_suite_passing=True,
        proactive_health_check=True,
        pricing_page_updated=False,
    ),
    Channel.GOOGLE_BUSINESS: ChannelReadiness(
        provider_audit_passed=False,
        publish_verified_live_on=None,
        reconciliation_implemented=False,
        conformance_suite_passing=False,
        proactive_health_check=False,
        pricing_page_updated=False,
    ),
    Channel.ZALO_OA: ChannelReadiness(
        provider_audit_passed=False,
        publish_verified_live_on=None,
        reconciliation_implemented=False,
        conformance_suite_passing=False,
        proactive_health_check=False,
        pricing_page_updated=False,
    ),
    Channel.EMAIL: ChannelReadiness(
        provider_audit_passed=False,
        publish_verified_live_on=None,
        reconciliation_implemented=False,
        conformance_suite_passing=False,
        proactive_health_check=False,
        pricing_page_updated=False,
    ),
}
