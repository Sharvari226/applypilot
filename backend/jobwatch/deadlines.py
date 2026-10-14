import json
from datetime import date, datetime
from pathlib import Path

items = json.loads((Path(__file__).parent / "programs.json").read_text(encoding="utf-8"))
today = date.today()

upcoming, unknown, passed = [], [], []
for p in items:
    if p.get("deadline"):
        days = (datetime.strptime(p["deadline"], "%Y-%m-%d").date() - today).days
        (upcoming if days >= 0 else passed).append((days, p))
    else:
        unknown.append(p)

print("== UPCOMING DEADLINES ==")
for days, p in sorted(upcoming, key=lambda x: x[0]):
    print(f"{days:>4} days  {p['deadline']}  {p['name']}\n           {p['note']}\n           {p['source']}")
print("\n== NO DATE YET (check periodically) ==")
for p in unknown:
    print(f"- {p['name']}: {p['note']}\n  {p['source']}")
print("\n== PASSED ==")
for days, p in passed:
    print(f"- {p['deadline']}  {p['name']}: {p['note']}")