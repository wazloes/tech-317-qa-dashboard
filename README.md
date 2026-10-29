# TECH-317 QA Dashboard
Open `index.html` directly (file:///workspace/tech-317-qa/rerun/dashboard/index.html), or:
    cd /workspace/tech-317-qa/rerun/dashboard && python3 -m http.server 8765   # http://127.0.0.1:8765/
Nav: Hub / §1 JWT / §2 OTP / §4 Hours / §7 Regression / Both-system bugs. Click any row to expand the full report; deep link e.g. `#otp/P-01`.
Rebuild data after reruns: `python3 build.py` (reads round2/*/cases/*.json verbatim into data/data.js; nothing hand-entered).
