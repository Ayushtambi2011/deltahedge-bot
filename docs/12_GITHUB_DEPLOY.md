# 12 — Deploy on GitHub Actions (free, no server)

The bot runs as scheduled GitHub Actions. No VPS, no SSH. Your keys live in encrypted
Actions Secrets; your trade logs live in the (PRIVATE) repo. Go phase by phase.

## Key facts / trade-offs (know these)
- Schedules are **best-effort** — a job can run several minutes late. Fine for daily jobs.
- Runners are wiped each run, so each workflow **commits data/ back to the repo** to persist.
- The repo MUST be **private** (it holds your trade log). Free GitHub Pages doesn't serve
  private repos, so the dashboard (optional) goes on **Netlify** instead (Phase 4).

---
## PHASE 1 — Put the project on GitHub (use GitHub Desktop = easiest)
1. Make a free account at **github.com**.
2. Install **GitHub Desktop** (desktop.github.com) and sign in.
3. GitHub Desktop → **File → Add local repository** → choose the `OPTIONS STRATEGIES`
   folder → when it says "not a git repository", click **create a repository** → **Create**.
4. Click **Publish repository** → **keep "Keep this code private" CHECKED** → Publish.
   (`.gitignore` already excludes `bot/.env`, so your keys are never uploaded.)

## PHASE 2 — Add your secrets (on github.com)
Repo → **Settings → Secrets and variables → Actions → New repository secret**. Add:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `DELTA_API_KEY`  and  `DELTA_API_SECRET`  (read-only)
- `COINGLASS_API_KEY` (optional; leave out if unused)
Secrets are encrypted and never visible in logs.

## PHASE 3 — Turn on and test
1. Repo → **Actions** tab → if prompted, click **"I understand my workflows, enable them"**.
2. Open **desk-brief** → **Run workflow** → run it manually. Within a minute you should get
   the morning brief on Telegram. Then test **desk-entry** the same way.
3. Once tested, they run automatically on schedule (UTC):
   - desk-brief 01:30 (07:00 IST) · desk-entry 03:30 (09:00 IST)
   - desk-monitor hourly · desk-nightly 20:00 (settle + heartbeat; Sun = learning review)
4. Check the repo — you'll see `data/` files updating after each run (that's the persistence).

> Scheduled workflows pause after 60 days of no repo activity. The daily commits keep it
> active, so it won't pause in normal use.

## PHASE 4 (optional) — Dashboard on Netlify (free, works with a private repo)
1. **netlify.com** → sign up with GitHub → **Add new site → Import an existing project**.
2. Pick your private repo. Build command: **(leave blank)**. Publish directory: **`.`** (root).
3. Deploy. Your dashboard is at `https://YOURSITE.netlify.app/web/dashboard.html`.
   It reads the `data/performance.json` your Actions commit, so it updates automatically.
   - Netlify rebuilds on every push; if you approach the free build limit, lower the
     monitor frequency (edit `.github/workflows/desk-monitor.yml` cron) or just view the
     dashboard by opening the file locally after a `git pull`.

## Changing the schedule or thresholds later
Edit the file, commit in GitHub Desktop, push. Actions pick up the change automatically.
Cron is UTC (IST = UTC + 5:30).

## If the daily Telegram stops
Check the **Actions** tab for a failed (red) run and open its log. GitHub also emails you
when a scheduled workflow fails.
