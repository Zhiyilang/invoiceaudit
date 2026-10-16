#!/usr/bin/env python3
"""
invoiceaudit — assertion suite (also what CI runs).

Why this exists: the repo is linked from the DEV.to Hacktoberfest article, so a
red badge is visible to readers. More importantly these assertions pin the
detector behaviour that the article claims, so a future edit cannot silently
make the write-up false.

Stdlib only. Run:  python eval.py
"""
from __future__ import annotations
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(HERE, "examples", "invoices.txt")
PY = sys.executable


def run_cli(*args):
    r = subprocess.run([PY, "-m", "invoiceaudit.cli", *args],
                       cwd=HERE, capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout, r.stderr


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"  {detail}" if detail else ""))
    return bool(cond)


def main() -> int:
    ok = True

    ok &= check("examples/invoices.txt exists", os.path.isfile(EXAMPLES))

    rc, out, err = run_cli(EXAMPLES)
    ok &= check("CLI exits 0 on the bundled example", rc == 0, f"rc={rc} {err[:120]}")
    ok &= check("CLI prints something", bool(out.strip()))

    for kw in ("重复", "税", "缺"):
        ok &= check(f"report mentions '{kw}'", kw in out)

    # --text path must work without a file on disk
    sample = ("INVOICE_ID: T-1\nAMOUNT: 100.00\nTAX: 13.00\n"
              "TOTAL: 113.00\nDATE: 2030-01-01\n")
    rc2, out2, err2 = run_cli("--text", sample)
    ok &= check("--text mode exits 0", rc2 == 0, f"rc={rc2} {err2[:120]}")
    ok &= check("--text mode flags the future date", "2030" in out2 or "未来" in out2)

    # --html must write a real file
    with tempfile.TemporaryDirectory() as d:
        html = os.path.join(d, "r.html")
        rc3, out3, err3 = run_cli(EXAMPLES, "--html", html)
        ok &= check("--html exits 0", rc3 == 0, f"rc={rc3} {err3[:120]}")
        ok &= check("--html wrote a non-empty report",
                    os.path.isfile(html) and os.path.getsize(html) > 200)

    # missing input must fail cleanly, not traceback
    rc4, out4, err4 = run_cli()
    ok &= check("no-arg exits non-zero", rc4 != 0, f"rc={rc4}")
    ok &= check("no-arg does not traceback", "Traceback" not in (out4 + err4))

    print("\nEVAL_OK" if ok else "\nEVAL_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
