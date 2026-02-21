#!/usr/bin/env python3
"""
Redfin Sacramento Associate Agent Job Alert
Checks Redfin careers for Associate Agent openings in Sacramento, CA
and sends a Twilio SMS when new listings appear.
"""

import os
import json
import time
from playwright.sync_api import sync_playwright

# ── Twilio SMS ────────────────────────────────────────────────────────────────
def send_sms(message: str):
    from twilio.rest import Client
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token  = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_FROM_NUMBER"]   # your Twilio number
    to_number   = os.environ["TWILIO_TO_NUMBER"]     # your personal number

    client = Client(account_sid, auth_token)
    client.messages.create(body=message, from_=from_number, to=to_number)
    print(f"✅ SMS sent: {message}")

# ── State helpers (persist job count between runs via a JSON file) ─────────────
STATE_FILE = "job_state.json"

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_count": 0, "alerted_ids": []}

def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ── Core scraper ──────────────────────────────────────────────────────────────
def get_sacramento_jobs() -> list[dict]:
    """
    Loads the Redfin Associate Agent careers page, applies the
    California / Sacramento filters, and returns the job listings found.
    """
    jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("🌐 Loading Redfin careers page...")
        page.goto(
            "https://careers.redfin.com/us/en/c/associate-agent-independent-contractor-jobs",
            wait_until="networkidle",
            timeout=60_000,
        )

        # ── Apply State = California filter ──────────────────────────────────
        print("🔍 Applying State filter: California...")
        try:
            # Open the State filter accordion / dropdown
            page.click("text=State", timeout=10_000)
            time.sleep(1)

            # Click "California" checkbox (label contains the text)
            page.click("text=California", timeout=10_000)
            time.sleep(2)  # wait for the page to re-filter
        except Exception as e:
            print(f"⚠️  Could not click State/California filter: {e}")

        # ── Apply City = Sacramento filter ────────────────────────────────────
        print("🔍 Applying City filter: Sacramento...")
        try:
            page.click("text=City", timeout=10_000)
            time.sleep(1)
            page.click("text=Sacramento", timeout=10_000)
            time.sleep(2)
        except Exception as e:
            print(f"⚠️  Could not click City/Sacramento filter: {e}")

        # ── Wait for results to settle ────────────────────────────────────────
        time.sleep(3)

        # ── Collect job cards ─────────────────────────────────────────────────
        # Phenom People job cards typically have a role="listitem" or a
        # data-ph-at-id attribute.  We try a few selectors.
        selectors = [
            "[data-ph-at-id='job-link']",
            "a[href*='/us/en/job/']",
            ".job-title",
            "[class*='jobTitle']",
            "[class*='job-title']",
        ]

        for sel in selectors:
            elements = page.query_selector_all(sel)
            if elements:
                print(f"✅ Found {len(elements)} element(s) with selector '{sel}'")
                for el in elements:
                    title = el.inner_text().strip()
                    href  = el.get_attribute("href") or ""
                    if href and not href.startswith("http"):
                        href = "https://careers.redfin.com" + href
                    if title:
                        jobs.append({"title": title, "url": href})
                break  # stop at first working selector
        else:
            # Fallback: check if the "no jobs" message is present
            content = page.content()
            if "There are no jobs" in content or "no jobs for your search" in content.lower():
                print("ℹ️  Page says: no jobs found for this filter.")
            else:
                print("⚠️  Could not parse job listings — dumping page text for debug:")
                print(page.inner_text("body")[:2000])

        browser.close()

    return jobs

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    state = load_state()
    print(f"📋 Last known job count: {state['last_count']}")

    jobs = get_sacramento_jobs()
    current_count = len(jobs)
    print(f"📋 Current job count: {current_count}")

    if current_count > 0 and current_count > state["last_count"]:
        # New job(s) appeared!
        new_count = current_count - state["last_count"]
        titles    = "\n• ".join(j["title"] for j in jobs)
        link      = jobs[0]["url"] if jobs[0]["url"] else \
                    "https://careers.redfin.com/us/en/c/associate-agent-independent-contractor-jobs"

        message = (
            f"🏠 Redfin Alert! {new_count} new Associate Agent job(s) in Sacramento!\n\n"
            f"• {titles}\n\n"
            f"Apply now: {link}"
        )
        send_sms(message)
        state["last_count"] = current_count

    elif current_count == 0 and state["last_count"] > 0:
        # Jobs disappeared — reset counter so we alert again next time they return
        print("ℹ️  Jobs gone. Resetting counter.")
        state["last_count"] = 0

    else:
        print("✅ No change in job count. No alert needed.")

    save_state(state)

if __name__ == "__main__":
    main()