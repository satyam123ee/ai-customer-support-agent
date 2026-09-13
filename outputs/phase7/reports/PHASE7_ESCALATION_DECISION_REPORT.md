# Phase 7 — Auto-Handle vs Escalation Decision Report

## Decision policy
Deterministic rule-based decision layer over Phase 5 evidence and Phase 6 grounded responses. Threshold: 0.35. Explicit account/security, billing/payment, and order/repair/service signals override otherwise usable evidence. Unresolved ambiguous/unclassified/multi-intent records with no gold intent are escalated. No external API/LLM.

## Results
- Total: 200
- Auto-handle: 117 (58.5%)
- Escalate: 83 (41.5%)
- Reasons: ambiguous_request 25; insufficient_historical_evidence 15; account_or_security_sensitive 14; billing_or_payment_case_specific 18; order_repair_case_specific 11.

## Auto-handle examples
- GS-004: @AppleSupport Battery down! Please🙏
  Evidence 1083939, score 0.702062; response: @375679 We want you to have a good battery. What is the exact issue that is happening with it?
- GS-005: @AppleSupport yes the battery
  Evidence 1083939, score 0.702062; response: @375679 We want you to have a good battery. What is the exact issue that is happening with it?
- GS-010: @AppleSupport It doesn't work!
  Evidence 1222380, score 0.6; response: @406832 Is the Wi-Fi icon greyed out? In Settings &gt; Wi-Fi, do you see Wi-Fi networks in the area?
- GS-011: @AppleSupport Still not working☹️
  Evidence 1414552, score 0.6; response: @448732 What model iPhone do you have? Let us know in a DM. https://t.co/GDrqU22YpT
- GS-013: @AppleSupport iPhone 7 Plus.   iOS 11.0.2
  Evidence 1064898, score 0.6; response: @245847 To clarify, does this issue only happen in the calculator app?

## Escalation examples
- GS-001: @applesupport MacPro 2013. Yosemite. iTunes 12.7.
  Reason: ambiguous_request
- GS-002: @AppleSupport 2/2 song from itunes https://t.co/xJ1yBfxuvJ
  Reason: ambiguous_request
- GS-003: @AppleSupport Same for music
  Reason: ambiguous_request
- GS-006: @AppleSupport WiFi and streaming.
  Reason: ambiguous_request
- GS-007: @AppleSupport Just Bluetooth Audio
  Reason: ambiguous_request

## Limitations
- This policy is deterministic and not human-validated.
- Keyword rules may create false positives/negatives.
- Historical evidence can still be contextually wrong.
- Phase 3E escalation values are preliminary references only, not gold labels.
- Human evaluation is required for retrieval relevance, response quality, grounding correctness, and escalation correctness.
