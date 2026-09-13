# Failure Analysis — Observed Risk / Failure Modes

These are observed risk modes in the 200-example golden set. They are not all proven model errors; some are deliberately conservative safety escalations. Examples are real dataset messages.

## 1. Ambiguous or incomplete requests — 25 escalations
**Example GS-001:** “@applesupport MacPro 2013. Yosemite. iTunes 12.7.”

**Why it is hard:** the message gives product/version context but no explicit problem. A lexical retriever can find superficially similar historical conversations without knowing what outcome the customer wants.

**Hypothesis:** ask a clarifying question or escalate instead of assuming the customer's goal.

## 2. Billing/payment case-specific requests — 18 escalations
**Example GS-020:** customer reports being charged twice for an iPad order and asks when the money will be returned.

**Why it is hard:** a historically similar reply cannot safely authorize a refund or make a claim about an individual payment.

**Hypothesis:** keep transaction-specific cases with a human unless the system has verified account/order tools.

## 3. Insufficient historical evidence — 15 escalations
**Example GS-021:** customer reports Mac migration failure and a Time Machine backup stuck for five hours.

**Why it is hard:** the closest historical messages are related to Time Machine but do not establish a reliable answer for this exact failure.

**Hypothesis:** evidence thresholds should prevent the system from turning topical similarity into unsupported advice.

## 4. Account/security-sensitive requests — 14 escalations
**Example GS-019:** customer reports being logged out of iCloud after an update and losing access to music/iMessage.

**Why it is hard:** account access and recovery are consequential; a copied historical response may not safely address the customer's specific account state.

**Hypothesis:** use conservative escalation until authenticated account tooling exists.

## 5. Order/repair/service cases — 11 escalations
**Example GS-027:** customer reports a macOS update failure and says an Apple Store appointment has already been booked.

**Why it is hard:** repair/service status is case-specific and may require current appointment, device, or warranty information.

**Hypothesis:** route to a human or authenticated service workflow rather than inventing status or eligibility.

## Important interpretation
The frequency of these categories should **not** be presented as an error rate. They describe where the current policy intentionally refuses to auto-handle or where historical evidence is weak. A future version should separately measure false escalations and missed escalations with independent human labels.
