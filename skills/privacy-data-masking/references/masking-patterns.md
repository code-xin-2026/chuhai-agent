# Masking Patterns

Use these as stable, readable replacements. Preserve the shape and the final digits only where needed for identification.

## Replacements

| Data | Replacement |
|---|---|
| Email | `[EMAIL]` |
| Phone | `[PHONE]` |
| Full address | `[ADDRESS]` |
| Card number | `[CARD...1234]` |
| IBAN / bank account | `[IBAN...1234]` |
| Passport / ID number | `[ID]` |
| Full name when not needed | `[CUSTOMER]` |
| Tracking number in public logs | `[TRACKING]` |
| Credentials, tokens, API keys | `[SECRET]` |

## Rules

1. Mask on capture and again before any output leaves the agent boundary.
2. Keep last-four-digit tails only when an operator genuinely needs them to identify a record.
3. Never reconstruct the full value from a masked form.
4. For RTL or mixed-script text, mask without breaking surrounding layout; keep Latin placeholder tokens.

## Example

Before:

```text
Customer jane@example.com, phone +44 7000 000000, IBAN GB00XXXX00000012345678 wants a refund.
```

After:

```text
Customer [EMAIL], phone [PHONE], IBAN [IBAN...5678] wants a refund.
```
