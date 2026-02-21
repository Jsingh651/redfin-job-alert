name: Redfin Job Alert

on:
  schedule:
    - cron: "0 * * * *"
  workflow_dispatch:

jobs:
  check-jobs:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Python packages
        run: pip install playwright

      - name: Install Playwright browsers
        run: playwright install --with-deps chromium

      - name: Restore job state
        uses: actions/cache@v4
        with:
          path: job_state.json
          key: job-state-${{ github.run_id }}
          restore-keys: |
            job-state-

      - name: Check Redfin for Sacramento jobs
        env:
          GMAIL_ADDRESS:      ${{ secrets.GMAIL_ADDRESS }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
        run: python check_jobs.py

      - name: Save job state
        uses: actions/cache@v4
        with:
          path: job_state.json
          key: job-state-${{ github.run_id }}
