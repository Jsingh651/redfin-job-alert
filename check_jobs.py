#!/usr/bin/env python3
"""
Redfin Sacramento Associate Agent Job Alert
Checks Redfin careers for Associate Agent openings in Sacramento, CA
and sends an email alert via Gmail when new listings appear.
"""

import os
import json
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright

# ── Email alert ───────────────────────────────────────────────────────────────
def send_email(subject: str, body: str):
    gmail_user     = os.environ["GMAIL_ADDRESS"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_user
    msg["To"]      = gmail_user
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, gmail_user, msg.as_string())

    print(f"✅ Email sent: {subject}")

# ── State helpers ─────────────────────────────────────────────────────────────
STATE_FILE = "job_state.json"

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_count": 0}

def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ── Core scraper ──────────────────────────────────────────────────────────────
def get_sacramento_jobs() -> list[dict]:
    all_jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("🌐 Loading Redfin careers page...")
        page.goto(
            "https://careers.redfin.com/us/en/c/associate-agent-independent-contractor-jobs",
            wait_until="networkidle",
            timeout=60_000,
        )

        time.sleep(4)

        selectors = [
            "[data-ph-at-id='job-link']",
            "a[href*='/us/en/job/']",
            "[class*='jobTitle'] a",
            "[class*='job-title'] a",
            ".job-title a",
        ]

        for sel in selectors:
            elements = page.query_selector_all(sel)
            if elements:
                print(f"Found {len(elements)} total job(s) with selector '{sel}'")
                for el in elements:
                    title = el.inner_text().strip()
                    href  = el.get_attribute("href") or ""
                    if href and not href.startswith("http"):
                        href = "https://careers.redfin.com" + href
                    if title:
                        all_jobs.append({"title": title, "url": href})
                break

        if not all_jobs:
            content = page.content()
            if "There are no jobs" in content or "no jobs for your search" in content.lower():
                print("ℹ️  No jobs found on the page at all.")
            else:
                print("⚠️  Could not parse job listings — page text:")
                print(page.inner_text("body")[:3000])

        browser.close()

    print(f"Total jobs found before location filter: {len(all_jobs)}")

    sacramento_keywords = ["sacramento", "elk grove", "roseville", "folsom", "rancho cordova"]

    sacramento_jobs = []
    for job in all_jobs:
        combined = (job["title"] + " " + job["url"]).lower()
        if any(kw in combined for kw in sacramento_keywords):
            sacramento_jobs.append(job)
            print(f"✅ Sacramento match: {job['title']}")
        else:
            print(f"⛔ Skipping (not Sacramento): {job['title']}")

    return sacramento_jobs

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    state = load_state()
    print(f"📋 Last known Sacramento job count: {state['last_count']}")

    jobs = get_sacramento_jobs()
    current_count = len(jobs)
    print(f"📋 Current Sacramento job count: {current_count}")

    if True:
        new_count = current_count - state["last_count"]
        titles    = "\n• ".join(j["title"] for j in jobs)
        link      = jobs[0]["url"] if jobs[0]["url"] else \
                    "https://careers.redfin.com/us/en/c/associate-agent-independent-contractor-jobs"

        subject = f"🏠 Redfin Alert! {new_count} new Associate Agent job(s) in Sacramento!"
        body    = (
            f"Good news! A new Associate Agent position opened up in Sacramento.\n\n"
            f"Jobs found:\n• {titles}\n\n"
            f"Apply now: {link}\n\n"
            f"-- Your Redfin Job Alert Bot"
        )
        send_email(subject, body)
        state["last_count"] = current_count

    elif current_count == 0 and state["last_count"] > 0:
        print("ℹ️  Sacramento jobs gone. Resetting counter.")
        state["last_count"] = 0

    else:
        print("✅ No change in Sacramento job count. No alert needed.")

    save_state(state)

if __name__ == "__main__":
    main()
