---
name: inquiry-intake
description: Turn an incomplete overseas-trade inquiry into a complete, structured RFQ record and ask only for the missing facts that change the answer; use for product inquiries, quotation requests, and sample requests.
---

# Inquiry Intake

Use this skill to qualify and complete a foreign-trade inquiry without interrogating the customer.

## Required fields

For a quotation or product inquiry, capture as much as possible of:

1. Product or model, revision, and required specification.
2. Quantity and unit (and MOQ context if relevant).
3. Destination country and port of delivery.
4. Incoterm (FOB, CIF, DDP, EXW, etc.).
5. Required or target delivery date.
6. Currency and payment-term preference when the customer raises payment.
7. Required certification, labeling, packaging, or target-market compliance.

For a sample request, also capture: sample quantity, delivery country, freight payer, and courier account if available.

## Rules

1. Extract what the customer already gave. Do not ask again for fields that are present.
2. Ask only for missing facts that materially change the answer. Group them into one short checklist in the customer's language.
3. If the product is ambiguous, ask for a photo, model number, drawing, SKU, or intended application.
4. Never assume quantity, destination, Incoterm, or dates. Treat inferred values as unconfirmed.
5. If a required field cannot be supplied now, mark it as `missing` and continue only if the answer is still safe; otherwise send a holding response.

## Output

Produce two parts:

1. A compact `Inquiry Record` (internal) with `confirmed` and `missing` fields.
2. A customer-ready message that asks for the missing fields and confirms what was understood.

Example internal record:

```text
product: confirmed (SKU-1234)
spec: missing
quantity: confirmed (1000 units)
destination: confirmed (Rotterdam, Netherlands)
incoterm: missing
delivery_date: missing
certification: confirmed (CE required)
```

Do not show the internal record to the customer; show only the reply.
