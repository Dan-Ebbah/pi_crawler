import time
from typing import Optional
import requests

DEFAULT_HEADERS = {
    "User-Agent": "PiCrawler/1.0 (contact: danielebbah@yahoo.com)"
}

def fetch_html(url: str,
               max_retries: int = 3,
               delay_seconds: float = 1.0) -> Optional[str]:
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
            if 200 <= resp.status_code < 300:
                return resp.text
            elif 500 <= resp.status_code < 600:
                time.sleep(delay_seconds * attempt)
            else:
                print(f"[WARN] {url} returned status code {resp.status_code}. Not retrying.")
                return None
        except requests.RequestException as e:
            print(f"[WARN] Error fetching {url}: {e}")
            time.sleep(delay_seconds * attempt)
    print(f"[ERROR] Failed to fetch {url} after {max_retries} attempts.")
    return None

