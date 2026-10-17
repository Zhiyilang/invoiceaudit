<!-- PUBLISH: title="My friend got paid four months late because nobody checked one invoice" tags="devchallenge,hf26challenge,ai,python" -->
A friend who freelances got paid four months late. Not because the client was broke - because a $2,847 invoice sat in someone's inbox marked "need to check with accounting," and nobody checked. She was too embarrassed to chase it, the client was too busy to look, and the money just... sat there.

The invoice itself had a problem too. Looking at it later, we found the tax line didn't add up: 8 items at 12% plus a 10% discount applied *before* tax instead of after. It was $61 off - small enough to slip through, big enough that her accountant noticed and she had to eat the correction.

**InvoiceAudit** is the tool I wish she'd had: an offline, zero-dependency invoice risk checker that reads your invoices before you send them and flags the things that delay or lose you money.

Week 4's theme is building with open-weight models and open-source AI tools, and InvoiceAudit is the deliberately model-free corner of that theme: pure Python standard library, no API keys, no uploads. The reasoning is simple — invoice data is the full financial picture of a business, so the most open-source-AI thing I could build is a tool where the data never leaves the machine and every check is a rule you can read in an afternoon.

## What it checks

You paste invoice text in a simple `KEY: VALUE` block format. InvoiceAudit parses it and runs seven transparent checks:

1. **DUPLICATE_INVOICE** - same invoice number seen twice: the classic double-payment trap
2. **TOTAL_MISMATCH** - the line items don't sum to the stated total
3. **TAX_RATE_MISMATCH** - the tax amount doesn't match the stated rate on the taxable base
4. **MISSING_FIELD** - no invoice number, date, due date, or tax ID: every missing field is a reason for accounts payable to stall
5. **ROUND_AMOUNT** - suspiciously round large amounts, a classic sign of placeholder numbers
6. **FUTURE_DATE** - an issue date in the future, which payment systems reject
7. **OVERDUE** - past the due date and still marked unpaid

Every finding comes with a severity (HIGH or CAUTION), the exact field values that triggered it, and a concrete fix suggestion. Then it gives the invoice an overall risk score and generates a shareable HTML report.

## A real run

Here's the checker working on its own example file (deliberately full of problems):

```
$ python -m invoiceaudit audit examples/invoices.txt

[HIGH]   DUPLICATE_INVOICE  invoice INV-2026-0412 appears 2 times
         -> two copies of the same invoice invite a double payment
[HIGH]   TOTAL_MISMATCH     items sum to 2847.00 but total says 2891.50
         -> line items and total disagree by 44.50
[HIGH]   TAX_RATE_MISMATCH  tax 89.70 on taxable base 2400.00 implies 3.7%, not the stated 12%
         -> recheck whether the discount was applied before or after tax
[HIGH]   MISSING_FIELD      invoice INV-2026-0518 has no due_date
         -> no due date means no payment clock
[CAUTION] ROUND_AMOUNT      invoice INV-2026-0533 total 5000.00 is suspiciously round
         -> confirm this is a real amount, not a placeholder
[CAUTION] FUTURE_DATE       invoice INV-2026-0541 issue date 2026-12-01 is in the future
         -> payment systems will reject a future issue date
[CAUTION] OVERDUE           invoice INV-2026-0399 due 2026-08-15 is 58 days overdue and unpaid
         -> chase it now, or write it off

Risk score: 100/100 (HIGH) - 2 HIGH, 5 CAUTION findings
HTML report written to report.html
```

The tax mismatch is the one I'm proudest of, because it's the bug that actually cost my friend money: the tool recomputes the implied rate from `tax / taxable_base` and compares it to the stated rate. When they disagree, the most common cause is a discount applied on the wrong side of the tax calculation - exactly the mistake in the story above.

## Why offline matters

Invoices contain client names, amounts, tax IDs - the full financial picture of a small business. InvoiceAudit runs entirely on your machine: pure Python standard library, no accounts, no uploads, no API keys. You can audit on an air-gapped laptop. There is no SaaS tier, because there is no server.

## Tech stack

- Pure Python stdlib (`re`, `datetime`, `argparse`) - clone and run, nothing to install
- Transparent rules with explainable output - every finding cites its field values
- HTML report for sharing with clients or accountants

## Try it

The repo is [github.com/Zhiyilang/invoiceaudit](https://github.com/Zhiyilang/invoiceaudit) with example invoices that trigger all seven checks, plus the full test suite. Clone it, run `python -m invoiceaudit audit examples/invoices.txt`, then point it at your own export.

If you bill clients for a living, you already know the two failure modes this tool targets: invoices that never get paid because something small is wrong with them, and invoices that get paid twice because nobody was checking. Both are cheaper to prevent than to chase.

What's the check you'd add? Mine is a candidate: **bank details changed mid-engagement** - the single most exploited invoice fraud pattern in existence.
