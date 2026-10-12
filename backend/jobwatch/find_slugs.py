import json
import sys

import requests

NAMES = sys.argv[1:] or [
    "anthropic", "databricks", "stripe", "cloudflare", "figma", "openai",
    "notion", "ramp", "palantir", "scaleai", "huggingface", "cohere",
    "postman", "browserstack", "razorpay", "groww",
]  # guesses only; the checks below decide which are real

URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{}/jobs",
    "lever": "https://api.lever.co/v0/postings/{}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{}",
}

found = {"greenhouse": [], "lever": [], "ashby": []}

for name in NAMES:
    for platform, url in URLS.items():
        try:
            r = requests.get(url.format(name), timeout=15)
            if r.status_code == 200:
                data = r.json()
                count = len(data["jobs"] if isinstance(data, dict) else data)
                print(f"OK   {platform:<10} {name:<15} {count} postings")
                found[platform].append(name)
        except Exception:
            pass

print("\nPaste into config.json (replace the existing three lines):")
for platform, slugs in found.items():
    print(f'  "{platform}": {json.dumps(slugs)},')