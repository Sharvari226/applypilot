import csv
import json
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).parent
CONFIG = json.loads((BASE / "pages.json").read_text(encoding="utf-8"))
SEEN_FILE = BASE / "seen_links.json"
OUT_FILE = BASE / "new_links.csv"
UA = "personal-job-watcher/0.4"
HEADERS = {"User-Agent": UA}


def allowed(url):
    """Respect robots.txt. If it can't be checked, skip the page."""
    p = urlparse(url)
    try:
        r = requests.get(f"{p.scheme}://{p.netloc}/robots.txt", headers=HEADERS, timeout=15)
    except Exception:
        return False
    if r.status_code in (401, 403):
        return False
    rp = RobotFileParser()
    rp.parse(r.text.splitlines() if r.status_code == 200 else [])
    return rp.can_fetch(UA, url)


def main():
    seen = set(json.loads(SEEN_FILE.read_text())) if SEEN_FILE.exists() else set()
    kws = [k.lower() for k in CONFIG["keywords"]]
    rows = []

    for page in CONFIG["pages"]:
        name, url = page["name"], page["url"]
        if not allowed(url):
            print(f"SKIPPED {name}: robots.txt disallows it or could not be checked")
            continue
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            r.raise_for_status()
        except Exception as e:
            print(f"WARNING {name}: {e}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        found = 0
        for a in soup.find_all("a", href=True):
            text = " ".join(a.get_text(" ").split())
            link = urljoin(url, a["href"]).split("#")[0]
            if len(text) < 8 or link in seen:
                continue
            if not any(k in text.lower() or k in link.lower() for k in kws):
                continue
            rows.append({"page": name, "text": text, "url": link,
                         "found_on": datetime.now().strftime("%Y-%m-%d")})
            seen.add(link)
            found += 1
        print(f"{name}: {found} new links")
        time.sleep(2)  # be polite

    if rows:
        with OUT_FILE.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    SEEN_FILE.write_text(json.dumps(sorted(seen)))
    print(f"{len(rows)} new links -> {OUT_FILE if rows else 'nothing written'}")


if __name__ == "__main__":
    main()