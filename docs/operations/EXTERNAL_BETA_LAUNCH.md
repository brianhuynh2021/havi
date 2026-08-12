# Havi External Beta Pilot Launch Guide

## Overview
This operational guide details the onboarding protocol, cohort selection criteria, onboarding script, feedback collection workflow, and SLA response targets for launching the Havi External Beta Cohort (10–20 Vietnamese business owners).

---

## 1. Target Pilot Cohort Profile

| Parameter | Criteria |
|---|---|
| **Target Size** | 10 to 20 active Vietnamese business owners |
| **Industries** | Spa/Clinic (30%), F&B & Cafe (25%), Real Estate (25%), Online Shops & Services (20%) |
| **Social Presence** | Must own an active Facebook Page or Zalo OA |
| **Technical Ability** | Non-technical (requires simple smartphone-first UI, zero prompt engineering) |

---

## 2. 3-Step Shop Onboarding Protocol

1. **Step 1: Account Activation & Industry Selection** (1 min)
   - Owner signs up at `/dangkypilot` or `/onboarding`.
   - Selects business industry (Spa, F&B, Real Estate, Online Shop, Other) and specifies banned claims or tone rules.
2. **Step 2: Social Channel Connection** (1 min)
   - Owner connects their Facebook Page via OAuth.
   - Verified by backend platform token encryption (`ConnectionRepository`).
3. **Step 3: First Content Job & 1-Click Approval** (1 min)
   - Owner inputs a 15s voice recording or quick photo.
   - Havi generates 3 multi-channel drafts (Facebook, Zalo, Google).
   - Owner reviews, makes minor edits if desired, and clicks **"Duyệt & đăng"** (Approve & Publish).

---

## 3. Support & Bug Triage SLAs

| Priority | Definition | Response Time Target | Resolution Target |
|---|---|---|---|
| **P0 (Blocker)** | Post failed to publish, credential leak, or app crash | < 30 minutes | < 2 hours |
| **P1 (High)** | LLM draft quality issue or scheduling delay | < 2 hours | < 12 hours |
| **P2 (Normal)** | Copy tweak or feature request | < 12 hours | < 48 hours |

---

## 4. Telemetry & Health Monitoring
Founders monitor pilot health daily using:
```bash
# Automated 7-Day Dogfooding & Health Audit
cd apps/backend && uv run python ../../scripts/dogfood_suite.py
```
Key Metrics to Track:
- % of drafts approved without owner edits vs edited
- Time from raw input to 1st approved post (< 90 seconds)
- Zero duplicate post incidents (100% idempotency protection)
