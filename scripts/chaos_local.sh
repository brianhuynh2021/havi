#!/usr/bin/env bash
# scripts/chaos_local.sh — Local Chaos & Resilience Suite for Havi Operations
#
# Kiểm tra khả năng chịu lỗi và tính đúng đắn vận hành của Havi:
# 1. Conformance suite (Contract testing cho publishers)
# 2. Token expiration mid-run & Health check alert
# 3. Ambiguous publish & reconciliation handling
# 4. Hash chain immutability & tamper detection
# 5. Outbox multi-batch draining & idempotency

set -euo pipefail

echo "========================================================"
echo "⚡ HAVI OPERATIONAL CHAOS & RESILIENCE SUITE"
echo "========================================================"

BACKEND_DIR="apps/backend"
cd "$BACKEND_DIR"

echo ""
echo "👉 [1/5] Running Publisher Conformance Contract Suite..."
uv run --python 3.12 pytest tests/conformance/test_publisher_contract.py -v

echo ""
echo "👉 [2/5] Running Channel Readiness & Health Alert Tests..."
uv run --python 3.12 pytest tests/test_channel_readiness.py tests/test_operations_health_alerts.py -v

echo ""
echo "👉 [3/5] Running Audit Hash Chain & Immutability Tests..."
uv run --python 3.12 pytest tests/test_audit_immutability.py -v

echo ""
echo "👉 [4/5] Running Idempotency, Publish Flow & Webhook Ingestion Tests..."
uv run --python 3.12 pytest tests/test_publish_flow.py tests/test_outbox.py tests/test_webhook_ingestion.py -v

echo ""
echo "👉 [5/5] Running Billing, Plan Limits & Past-Due Grace Policy Tests..."
uv run --python 3.12 pytest tests/test_billing_flow.py tests/test_plan_limits.py -v

echo ""
echo "========================================================"
echo "✅ ALL CHAOS & RESILIENCE CHECKS PASSED!"
echo "========================================================"
