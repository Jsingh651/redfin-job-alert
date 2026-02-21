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
    gmail_user     = os.environ["GMAIL_ADDRESS"]       # jangsing02@gmail.com
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]  # 16-char app password

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_user
    msg["To"]      = gmail_user  # sending to yourself
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
            page.click("text=State", timeout=10_000)
            time.sleep(1)
            page.click("text=California", timeout=10_000)
            time.sleep(2)
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

        time.sleep(3)

        # ── Collect job cards ─────────────────────────────────────────────────
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
                break
        else:
            content = page.content()
            if "There are no jobs" in content or "no jobs for your search" in content.lower():
                print("ℹ️  Page says: no jobs found for this filter.")
            else:
                print("⚠️  Could not parse job listings — page text:")
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
        print("ℹ️  Jobs gone. Resetting counter.")
        state["last_count"] = 0

    else:
        print("✅ No change in job count. No alert needed.")

    save_state(state)

if __name__ == "__main__":
    main()
