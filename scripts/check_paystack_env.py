from pathlib import Path

from dotenv import dotenv_values

from warehouse_ledger.config import get_settings

p = Path(__file__).resolve().parents[1] / ".env"
print("env_file", p)
print("exists", p.is_file(), "bytes", p.stat().st_size if p.is_file() else 0)
v = dotenv_values(p)
sk = (v.get("PAYSTACK_SECRET_KEY") or "").strip()
pk = (v.get("PAYSTACK_PUBLIC_KEY") or "").strip()
print("dotenv secret_len", len(sk), "public_len", len(pk))
if len(sk) >= 7:
    print("secret_prefix", sk[:7])
get_settings.cache_clear()
s = get_settings()
print("settings secret_len", len(s.paystack_secret_key), "public_len", len(s.paystack_public_key))
text = p.read_text(encoding="utf-8-sig") if p.is_file() else ""
for i, line in enumerate(text.splitlines(), 1):
    if "PAYSTACK" in line.upper():
        parts = line.split("=", 1)
        val = parts[1].strip() if len(parts) == 2 else ""
        for q in ('"', "'"):
            if len(val) >= 2 and val[0] == q and val[-1] == q:
                val = val[1:-1]
        print("line", i, parts[0].strip(), "value_len", len(val))

print("all_keys", {k: len((val or "").strip()) for k, val in v.items()})