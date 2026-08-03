#!/usr/bin/env bash
# One-shot VPS setup for the DeltaHedge desk. Run ONCE on a fresh Ubuntu server:
#   bash deploy/setup_vps.sh
# It installs Python + deps, creates data dirs, and installs the cron schedule
# (entry, monitor, tracker, heartbeat) with correct absolute paths.
set -euo pipefail

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
echo "Project: $PROJECT"

echo "==> Installing Python + pip"
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip

echo "==> Installing Python deps"
pip3 install -r "$PROJECT/bot/requirements.txt" 2>/dev/null \
  || pip3 install --break-system-packages -r "$PROJECT/bot/requirements.txt"

mkdir -p "$PROJECT/data/chains"

PY="$(command -v python3)"
echo "==> Installing cron (times in UTC; IST = UTC + 5:30)"
CRON=$(cat <<EOF
# ===== DeltaHedge desk (auto-installed) — times UTC =====
30 3 * * *   cd "$PROJECT/bot" && $PY run_desk.py --mode entry   >> "$PROJECT/data/desk.log" 2>&1
*/10 * * * * cd "$PROJECT/bot" && $PY run_desk.py --mode monitor >> "$PROJECT/data/mon.log"  2>&1
0 20 * * *   cd "$PROJECT/bot" && $PY paper_tracker.py           >> "$PROJECT/data/perf.log" 2>&1
0 3 * * *    cd "$PROJECT/bot" && $PY heartbeat.py               >> "$PROJECT/data/beat.log" 2>&1
30 1 * * *   cd "$PROJECT/bot" && $PY daily_brief.py            >> "$PROJECT/data/brief.log" 2>&1
0 21 * * 0   cd "$PROJECT/bot" && $PY learning_review.py        >> "$PROJECT/data/learn.log" 2>&1
# daily_brief = 01:30 UTC = 07:00 IST (news + market structure + S/R). Weekly section auto-adds Mondays.
# learning_review runs Sunday night (settled-trade review). Needs ~15 settled trades to draw lessons.
# ========================================================
EOF
)
# replace any previous DeltaHedge cron block, keep the rest
( crontab -l 2>/dev/null | grep -v 'DeltaHedge\|run_desk.py\|paper_tracker.py\|heartbeat.py' || true; echo "$CRON" ) | crontab -

echo "==> Done."
echo "Next:"
echo "  1) Edit your secrets:   nano $PROJECT/bot/.env   (Telegram + read-only Delta keys; set DRY_RUN=false)"
echo "  2) Test one run now:     cd $PROJECT/bot && $PY run_desk.py --mode entry"
echo "  3) Verify cron:          crontab -l"
echo "  4) (optional) serve dashboard: cd $PROJECT && $PY -m http.server 8080"
