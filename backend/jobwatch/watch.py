import csv
import html
import json
import os
import re
from datetime import datetime
from pathlib import Path

import requests

BASE = Path(__file__).parent  # paths work no matter where you run it from
CONFIG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
SEEN_FILE = BASE / "seen.json"
OUT_FILE = BASE / "new_jobs.csv"
HEADERS = {"User-Agent": "personal-job-watcher/0.2"}

RESTRICTION_PATTERNS = [
    r"authori[sz]ed to work in the (?:united states|u\.s\.|us|uk|united kingdom|canada|eu)\b",
    r"\b(?:us|u\.s\.|usa|uk|canada) only\b",
    r"(?:us|u\.s\.|united states) (?:citizens?|persons?)\b",
    r"security clearance",
    r"no (?:visa )?sponsorship|(?:without|not) (?:require|need)[a-z ]*sponsorship",
    r"must (?:be located|reside|live) in",
]


def get_json(url, **kwargs):
    r = requests.get(url, headers=HEADERS, timeout=25, **kwargs)
    r.raise_for_status()
    return r.json()


def clean(text):
    """Decode HTML entities and strip tags (Greenhouse returns escaped HTML)."""
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


# ---------- sources ----------
def fetch_greenhouse(slug):
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    for j in data.get("jobs", []):
        yield {
            "id": f"gh:{slug}:{j['id']}",
            "company": slug,
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "description": clean(j.get("content")),
        }


def fetch_lever(slug):
    for j in get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
        yield {
            "id": f"lv:{slug}:{j['id']}",
            "company": slug,
            "title": j.get("text", ""),
            "location": (j.get("categories") or {}).get("location", "") or "",
            "url": j.get("hostedUrl", ""),
            "description": j.get("descriptionPlain", "") or "",
        }


def fetch_ashby(slug):
    data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    for j in data.get("jobs", []):
        yield {
            "id": f"ab:{slug}:{j['id']}",
            "company": slug,
            "title": j.get("title", ""),
            "location": j.get("location", "") or "",
            "url": j.get("jobUrl", ""),
            "description": j.get("descriptionPlain", "") or "",
        }


def fetch_remotive(_):
    data = get_json("https://remotive.com/api/remote-jobs")
    for j in data.get("jobs", []):
        yield {
            "id": f"rm:{j['id']}",
            "company": j.get("company_name", ""),
            "title": j.get("title", ""),
            "location": "Remote - " + (j.get("candidate_required_location") or ""),
            "url": j.get("url", ""),
            "description": clean(j.get("description")),
        }


def fetch_remoteok(_):
    data = get_json("https://remoteok.com/api")
    for j in data:
        if not isinstance(j, dict) or "id" not in j:
            continue  # first element is a legal notice, not a job
        yield {
            "id": f"ro:{j['id']}",
            "company": j.get("company", ""),
            "title": j.get("position", ""),
            "location": "Remote - " + (j.get("location") or ""),
            "url": j.get("url", ""),
            "description": clean(j.get("description")),
        }


def fetch_adzuna(query):
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        raise RuntimeError("ADZUNA_APP_ID / ADZUNA_APP_KEY not set (skipping)")
    data = get_json(
        "https://api.adzuna.com/v1/api/jobs/in/search/1",
        params={"app_id": app_id, "app_key": app_key, "results_per_page": 50,
                "what": query, "content-type": "application/json"},
    )
    for j in data.get("results", []):
        yield {
            "id": f"az:{j['id']}",
            "company": (j.get("company") or {}).get("display_name", ""),
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("display_name", ""),
            "url": j.get("redirect_url", ""),
            "description": clean(j.get("description")),  # Adzuna gives only a snippet
        }


# ---------- filters and flags ----------
def has_word(text, kw):
    return re.search(rf"\b{re.escape(kw)}\b", text) is not None


def location_ok(loc):
    if not loc.strip():
        return True  # unknown location: keep it, check manually
    if any(has_word(loc, k) for k in CONFIG.get("exclude_regions", [])):
        return False
    return any(has_word(loc, k) for k in CONFIG["location_keywords"])


def matches(job):
    title = job["title"].lower()
    if not any(has_word(title, k) for k in CONFIG["title_keywords"]):
        return False
    if any(has_word(title, k) for k in CONFIG["exclude_keywords"]):
        return False
    return location_ok(job["location"].lower())


def skill_hits(job):
    text = (job["title"] + " " + job["description"]).lower()
    return [s for s in CONFIG["my_skills"] if s in text]


def years_required(job):
    text = job["description"].lower()
    nums = [int(n) for n in re.findall(r"(\d{1,2})\s*\+?\s*(?:-\s*\d+\s*)?years?[^.]{0,40}experience", text)]
    return max(nums) if nums else 0


def restriction_flags(job):
    text = job["description"].lower()
    found = []
    for p in RESTRICTION_PATTERNS:
        m = re.search(p, text)
        if m:
            found.append(m.group(0))
    return "; ".join(found)


def main():
    seen = set(json.loads(SEEN_FILE.read_text())) if SEEN_FILE.exists() else set()

    sources = []
    sources += [("greenhouse", fetch_greenhouse, s) for s in CONFIG.get("greenhouse", [])]
    sources += [("lever", fetch_lever, s) for s in CONFIG.get("lever", [])]
    sources += [("ashby", fetch_ashby, s) for s in CONFIG.get("ashby", [])]
    boards = {"remotive": fetch_remotive, "remoteok": fetch_remoteok}
    sources += [(b, boards[b], None) for b in CONFIG.get("remote_boards", []) if b in boards]
    sources += [("adzuna", fetch_adzuna, q) for q in CONFIG.get("adzuna_queries", [])]

    new_rows = []
    for name, fetch, arg in sources:
        try:
            for job in fetch(arg):
                if job["id"] in seen or not matches(job):
                    continue
                hits = skill_hits(job)
                new_rows.append(
                    {
                        "company": job["company"],
                        "title": job["title"],
                        "location": job["location"],
                        "skill_hits": len(hits),
                        "skills_mentioned": ", ".join(hits),
                        "years_required": years_required(job),
                        "restriction_flags": restriction_flags(job),
                        "url": job["url"],
                        "source": name,
                        "found_on": datetime.now().strftime("%Y-%m-%d"),
                        "grad_years": grad_years(job),
                    }
                )
                seen.add(job["id"])
        except Exception as e:
            print(f"WARNING {name}/{arg}: {e}")

    # realistic roles first: low experience requirement, then most skill matches
    new_rows.sort(key=lambda r: (r["years_required"] >= 3, -r["skill_hits"]))
    if new_rows:
        with OUT_FILE.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(new_rows[0].keys()))
            w.writeheader()
            w.writerows(new_rows)
    SEEN_FILE.write_text(json.dumps(sorted(seen)))
    print(f"{len(new_rows)} new matching jobs -> {OUT_FILE if new_rows else 'nothing written'}")

def grad_years(job):
    """Years mentioned near 'graduat' / 'class of' (e.g. '2027'), for eligibility triage."""
    text = job["description"].lower()
    found = set()
    for m in re.finditer(r"graduat|class of", text):
        window = text[max(0, m.start() - 60): m.end() + 80]
        found.update(re.findall(r"\b(20\d{2})\b", window))
    return ",".join(sorted(found))

if __name__ == "__main__":
    main()