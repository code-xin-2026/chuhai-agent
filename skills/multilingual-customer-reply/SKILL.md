---
name: multilingual-customer-reply
description: Detect a customer's language and draft the reply in that language with the right formality; use when replying to non-English or multilingual customer messages and when language confidence or style matters.
---

# Multilingual Customer Reply

Use this skill whenever the customer's language is unknown, non-English, or mixed, or when a reply must match the customer's language and register.

## Detection

1. Detect the language and dialect when possible: English (US/UK), Spanish (Latin American vs Castilian), Arabic (MSA vs a regional dialect), French, Portuguese (BR vs PT), Russian, German, Chinese, and others the customer may use.
2. If confidence is high, reply in that language. If confidence is low, do not guess silently: reply with a short bilingual clarification in English plus the most likely detected language.
3. Treat product codes, SKUs, prices, dates, quantities, currencies, and Incoterms as language-neutral and keep them exact. Do not translate SKUs, HS-like codes, or tracking numbers.

## Style

1. Match formality to the customer: use the correct address forms (`usted` vs `tu`, `vous` vs `tu`, `Sie` vs `du`, and Arabic/Japanese polite forms as appropriate).
2. Use natural, native-sounding business phrasing, not literal machine translation. Adapt idiomatic phrases instead of translating them word-for-word.
3. Keep the customer-facing reply short, direct, and B2B professional. Preserve the customer's original name spelling and attachments.
4. For right-to-left languages, keep structure readable and keep Latin product codes/prices in Latin script.

## Workflow

1. Translate the customer message into your internal working language for reasoning, flagging any ambiguous or culturally specific phrase.
2. Apply the relevant trade skill (inquiry intake, approved-data-only, trade-reply-templates, or trade-risk-escalation) to decide the substance of the reply.
3. Draft the reply in the customer's language.
4. If the content touches legal, customs, sanctions, payment-risk, or compliance topics, escalate to a human rather than translating a definitive commitment.

## Reference

Read `references/language-style-guide.md` for per-language trade-reply notes.
