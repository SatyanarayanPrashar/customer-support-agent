

## 2.1 Accepted payment methods


● Credit/debit cards (Visa, MasterCard, American Express)
● UPI and netbanking (India-specific)
● PayPal
● Bank transfers (for bulk or B2B orders — allow 5 business days for reconciliation)
● Gift cards / store credit
Agent note: Only accept the payment methods enabled in the merchant
dashboard. For suspicious or international card payments, consult the FraudOps
team.

## 2.2 Invoices and receipts


● Every paid order should generate a receipt emailed to the customer immediately.
● Tax details, order number, line items (robot model, accessories, warranty add-ons),
shipping charges, discounts, and total must appear on the invoice.
● Agents can re-issue invoices on request when the customer provides the order
number and billing email.

### Re-issuing an invoice: quick steps

1. Verify customer identity: ask for order number and last 4 digits of the card used or
    registered email.
2. Pull the order in the admin portal.
3. Generate a new PDF invoice and email it to the customer, CC-ing
    billing@company.example.
4. Log action in CRM.

## 2.3 Subscriptions & recurring payments


● If the product uses a subscription model (e.g., filter subscription, cloud-mapping
features), the customer will be charged on the renewal date.
● Subscriptions may be monthly, quarterly, or annually.
● Proration rules: If a customer upgrades mid-cycle, charge prorated difference. If they
downgrade, the downgrade takes effect at next renewal unless the company policy
allows immediate prorated credit.

## 2.4 Taxes and duties


● Sales tax/VAT/GST is applied according to shipping address and local law.
● For cross-border orders, customs/duties may be charged on import. Agents must
inform customers that these are handled by the courier unless the company explicitly
prepaid them.

# 3. Billing issue handling — scenarios &

# steps
Each scenario below includes a short script, the investigation steps, and the expected
resolution timeline.

## 3.1 Duplicate charges (same amount charged more than once)

**Agent steps:**

1. Verify order number, transaction IDs, and dates. Ask the customer to confirm the
    exact amounts and dates.
2. Check payment gateway transaction logs and order status in admin portal.
    ○ If two successful payments exist for the SAME order, mark as
       duplicate_charge.
    ○ If one payment is pending or authorized and another captured, verify
       whether the authorization expired.
3. If duplicate charge confirmed and the product was shipped only once, initiate refund
    for the duplicate charge.
4. Notify the customer with a clear timeline (example: refund initiated and should reflect
    in 3–7 business days depending on bank).
5. Log a fraud/chargeback ticket if the duplicate appears to result from gateway issues.
**Expected timeline:** Refund initiated within 24 business hours once confirmed.
**Sample agent line:** “I see two successful transactions for this order. I will start a refund for
the duplicate charge right away and it should show in your bank statement within 3–
business days. I’ll send you a confirmation email as soon as it’s done.”

## 3.2 Mistake in calculation (e.g., discounts or taxes applied incorrectly)

**Customer says:** “My invoice shows the wrong discount/tax.”
**Agent steps:**

1. Request order number and billing email.


2. Pull applicable promotions and tax rate for that shipping address and order date.
3. Recalculate line items manually or using internal tool. Compare to recorded invoice.
4. If agent error (e.g., wrong promo code applied), correct the invoice and issue the
    difference as a refund or store credit per company policy.
5. If tax was undercollected, explain to customer and provide options: pay the balance
    or accept adjusted invoice (if legally required).
**Expected timeline:** Correction and refund within 48 business hours.
**Sample agent line:** “Thanks — I recalculated your invoice and found that the 10% welcome
discount wasn’t applied. I’ll issue a refund of ₹X to your original payment method now and
email you the corrected invoice.”

## 3.3 Charge failed but order created (authorization held)

**Customer says:** “I got an order confirmation but my card shows no charge.”
**Agent steps:**

1. Verify the order status. If status is created with an authorization but not
    captured, explain that the bank may hold authorization for 1–7 days and then
    release it.
2. If payment was never captured and order should not proceed, cancel the order and
    instruct Finance to release the authorization.
3. Confirm with the customer once release is visible.
**Expected timeline:** Authorization release depends on the bank (typically 1–7 days).
Cancellation processed within 24 hours.

## 3.4 Refund requested for accessories or consumables (non-returnable items)

**Agent steps:**

1. Check product returnability policy for that SKU.
2. If non-returnable but faulty within warranty, route to warranty claim flow.


3. If non-returnable and the request is not within warranty, explain policy politely and
    offer store credit as a gesture if appropriate.
**Sample agent line:** “This accessory is typically non-returnable, but since you report a defect
within 14 days, I’ll start a warranty claim. Please share photos and serial numbers so we can
proceed.”

## 3.5 Chargeback or dispute from customer bank

**Agent steps:**

1. Ask for copy of bank dispute if available and log the chargeback case ID.
2. Escalate to the Finance/Chargeback team and provide order, delivery, and
    transaction evidence.
3. Inform the customer that we are reviewing and may reach out for further evidence.
**Expected timeline:** Chargeback resolution varies (usually 30–90 days). Keep customer
updated weekly.

# 4. Refund policy — types, eligibility &

# workflows

## 4.1 Types of refunds


● Full refund: full order amount refunded (product returned in original condition per
policy)
● Partial refund: part of the order refunded (e.g., missing items, discount corrections)
● Pro-rated refund: for subscriptions canceled mid-cycle
● Store credit: non-cash credit for future purchases

## 4.2 Refund eligibility (sample, educational)



● Refunds for unopened robots within 14 days of delivery with original packaging:
eligible for full refund minus shipping (unless company offers free returns).
● Opened but defective robots within 30 days: eligible for repair or replacement under
warranty; refund possible if repair/replace not feasible.
● Consumables and accessories: refundable only if defective or within a short return
window (e.g., 7–14 days).
Agent note: Always confirm the company’s official return window and financial
limits before approving an exception.

## 4.3 Refund workflows & timelines

1. **Customer requests refund** → Agent verifies order and eligibility → Agent creates a
    refund_request case in CRM.
2. **Evidence check** (photos, videos, order status, delivery confirmation) → If evidence
    sufficient, approve refund.
3. **Finance issues refund** to original payment method. Note the time ranges each
    payment type takes to show in customer accounts.
**Typical timeline:**
● Agent approval: within 1 business day
● Finance processing: within 2 business days after approval
● Customer bank posting: 3–10 business days (card) / 5–15 business days (bank
transfer) / 1–3 business days (PayPal)

## 4.4 Refund for shipping and customs


● Refund of shipping cost: only when return is due to company error (wrong item or
damaged on arrival) unless policy states otherwise.
● Customs/duties: usually non-refundable unless company pre-paid and can recover
the charges.

## 4.5 Partial refunds due to damage or wear


● If the returned robot has damage beyond normal use, apply a restocking/damage
fee. The fee should be communicated and agreed upon prior to refund issuance.
**Agent sample:** “We received the returned unit and found a broken brush assembly beyond
normal use. Per our policy, a ₹X damage deduction applies; we will refund ₹Y after
deduction. Do you want to proceed?”

# 5. Warranty policy — coverage,

# exclusions, and claim handling

## 5.1 Warranty basics (sample educational policy)


● Standard manufacturer warranty: 12 months from date of delivery for the robot
(excluding wear items like brushes, filters, and batteries beyond an initial warranty
period).
● Wear items coverage: Brushes and filters have a 3–6 month warranty for
manufacturing defects only.
● Battery warranty: 12 months, but subject to capacity degradation limits (e.g., retains
at least 70% capacity to be covered).
Agents: Always quote the exact warranty period shown on the product page and
invoice. This section is an educational template.

## 5.2 What warranty covers (typical items)


● Manufacturing defects in hardware (motors, sensors, mainboard)
● Faulty assembly or failing components under normal use
● Software faults that render the device inoperable (if covered by company updates)

## 5.3 Warranty exclusions (common)


● Accidental damage (drops, water immersion beyond IP rating)



● Unauthorized repairs or modifications
● Normal cosmetic wear and tear (scratches, scuffs)
● Consumable exhaustion (brushes, filters) unless failing due to manufacturing defect
● Damage due to using non-approved chargers or accessories
● Software issues caused by third-party integrations or user-modified firmware

## 5.4 Warranty claim workflow (agent steps)

1. **Intake:** Collect order number, model, serial number, purchase date, and a clear
    description of the problem.
2. **Initial troubleshooting:** Follow the device-specific checklist (power cycle, reset,
    sensor cleaning guide, firmware update). Document each step and result.
3. **Evidence collection:** Ask for photos, video of the fault, and logs if the device can
    export them. For intermittent faults, request a short video showing the behavior.
4. **Remote diagnosis:** If the device is online and supports remote diagnostics, request
    a remote session.
5. **Decision point:** Based on evidence:
    ○ **Repairable remotely:** provide instructions or remote fix.
    ○ **Repair at service center:** Initiate RMA and provide the customer with
       shipping instructions.
    ○ **Replace:** If unit is dead on arrival or irreparable, and within warranty, approve
       replacement.
6. **RMA & shipping:** Generate RMA number, shipping label (if policy allows), and
    expected timelines.
7. **Service center processing:** Track ETA for repair/replace and update customer.
8. **Closure:** After repair/replace/refund, confirm with customer and close the ticket;
    ensure return shipping and final invoice reflected in CRM.
**Expected timeline:** Initial triage within 24–48 business hours. Repair or replacement usually
within 7–21 business days depending on part availability.


## 5.5 RMA and return shipping logistics


● RMA label issuance: company covers return shipping when defect confirmed. For
user-originated returns (change of mind), customer pays return shipping unless local
law states otherwise.
● Packing instructions: customer should follow detailed packing steps to avoid transit
damage. If returned unit arrives more damaged than reported, inspection may reduce
refund value.
● Tracking and handover: customer should provide tracking number; agent must log it.

## 5.6 Repair vs Replace decision rules (sample)


● Replace when: device is DOA (dead on arrival), repair cost > 60% of replacement
cost, or same failure repeated in a repaired unit.
● Repair when: single component failure that is cheaper and quicker to fix, or when
replacement is out of stock and repair is feasible.

# 6. Escalation matrix & SLAs

## 6.1 SLA targets (sample)


● First response (billing/warranty inquiries): within 4 business hours.
● Billing resolution (simple issues like invoice reissue, authorization release): within 24
business hours.
● Refund approval decision: within 48 business hours.
● Warranty triage and RMA decision: within 48 business hours.
● Chargeback handling: acknowledge within 1 business day; escalate to Finance
immediately.

## 6.2 Escalation paths


● **Level 1 (Agent):** handle basic billing questions, invoice reissues, gather evidence for
warranty.
● **Level 2 (Billing Specialist/Technical Support):** complex billing discrepancies,
gateway errors, refund approvals above a threshold (e.g., >₹50,000), remote
diagnostics.
● **Level 3 (Finance/Operations/Legal):** chargebacks, fraud, legal disputes, warranty
policy exceptions, cross-border tax issues.
**When to escalate immediately:**
● Suspected fraud.
● Chargebacks initiated by customer.
● Customer threatens legal action.
● Payment gateway outage affecting many customers.

# 7. Agent scripts, email templates &

# checklists

## 7.1 Quick verification script (phone/chat)

1. "Can I please have your full name and the order number?"
2. "For security, please confirm the billing email or the last 4 digits of the card used."
3. "I’ll look this up and get back to you with a clear next step within 24 hours."

## 7.2 Refund approval email (sample)

Subject: Refund Approved — Order #{{order_number}}
Hi {{first_name}},
Thanks for your patience. We’ve approved a refund of {{amount}} for Order
#{{order_number}}. The refund will be issued to the original payment method and should
appear on your statement within 3–10 business days depending on your bank.


If you have any questions, reply to this email and I’ll help you.
Best,
Customer Support — Billing Team

## 7.3 RMA initiation email (sample)

Subject: RMA Created — Order #{{order_number}} (RMA {{rma_number}})
Hi {{first_name}},
We have created an RMA for your unit ({{model}}). Please use the attached shipping label
and packing instructions. Once we receive the unit, our technicians will evaluate it and we
will update you within 7–14 business days.
RMA summary:

- RMA number: {{rma_number}}
- Ship-to address: {{address}}
- Expected processing time: 7–14 business days
Regards,
Customer Support — Warranty Team

## 7.4 Billing checklist (agent)


● Confirm identity and order number.
● Pull invoice and payment transaction IDs.
● Check promotions, coupons, and tax rates on order date.
● Confirm shipping status and whether goods were delivered.
● Provide clear next steps and timelines.
● Create or update CRM ticket with decisions and actions.

## 7.5 Warranty checklist (agent)


● Verify serial number and purchase date.
● Ask for photos/videos of the fault.
● Walk through basic troubleshooting steps.
● Create RMA if needed and provide shipping label.
● Track shipment and update ticket until closure.

# 8. Required evidence & documentation

## 8.1 For billing issues


● Order number and billing email.
● Transaction reference IDs from the customer (if available) and gateway logs.
● Screenshots of bank statements showing charges (masking unrelated data).

## 8.2 For warranty claims


● Photos and short video showing the fault.
● Serial number, model number, and purchase invoice.
● Device logs (if device supports logs) or error codes.
● Date/time of the issue and steps already taken by customer.

## 8.3 Acceptable formats and size limits


● Photos: JPEG/PNG, <10 MB each.
● Videos: MP4/MOV, <50 MB preferred; ask for short clips (10–30 seconds).

# 9. Edge cases & special considerations


## 9.1 International returns and duties


● For cross-border returns where customs/duties were paid by the customer, consult
Operations if refunding these fees is possible. Often the customer must file for a
refund with the courier or customs.

## 9.2 Lost-in-transit returns


● If return tracking shows lost package: open a claims case with courier and consider
issuing a provisional refund after appropriate verification.

## 9.3 Refusal by customer to accept repair or replacement


● If a customer refuses repair or replacement but wants refund outside the normal
return window, escalate to Level 3 for an exception review.

## 9.4 Fraud detection


● If multiple charge disputes or mismatched shipping/billing addresses, flag in CRM
and escalate to FraudOps.

# 10. Appendix

## 10.1 Sample decision matrix (billing vs warranty vs refund)


● Item never opened, within 14 days → refund (billing return)
● Item opened & defective within warranty → warranty RMA (repair/replace) — refund
if cannot be fixed
● Item damaged by user → charge for repair; partial refund only at discretion


## 10.2 Quick reference: timelines


● First response: 4 business hours
● Billing correction/refund initiation: 24–48 business hours
● Warranty triage: 24–48 business hours
● Repair/replace: 7–21 business days

## 10.3 Sample short chat responses

● Duplicate charge accepted: "I see the duplicate. I'll process a refund for that second
charge now — you'll see it in 3–7 business days."
● Refund denied due to policy: "I understand your concern. Based on our policy, this
item is outside the return window. I can offer store credit of ₹X as a gesture — would
that help?"
● RMA update: "Your RMA {{rma_number}} arrived at our service center today.
Technicians estimate completion by {{date}}. I'll update you if anything changes."
**End of document**
_Notes for trainers:_ adapt all timeline numbers, monetary symbols, and legal language to local
law before making this a live policy. This document deliberately uses conservative, clear
language intended for agent training.


