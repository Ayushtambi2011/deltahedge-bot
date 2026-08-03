# 08 — VPS Deploy (run 24/7, laptop off)

Your laptop can't do this — when it sleeps, everything stops. A VPS (small always-on cloud
server) runs the desk 24/7 and sends your daily Telegram whether your laptop is on or off.

## Step 0 — Pick a server
- **Oracle Cloud "Always Free"** — ₹0/month forever, India region. Fiddlier signup, occasional
  outages. Best if you want zero cost. (Pick an **Ubuntu 22.04** ARM/AMD instance.)
- **Hetzner (~₹330/mo)** — rock-solid, simplest. Best if you want no babysitting.
Our workload is tiny; the smallest instance is plenty.

Create the server, choose **Ubuntu 22.04**, and note its **IP address** and login user
(usually `ubuntu` or `root`).

## Step 1 — Get the Telegram bot (5 min, do this first)
1. In Telegram, message **@BotFather** → send `/newbot` → follow prompts → copy the **token**.
2. Message your new bot once (say "hi"), then message **@userinfobot** to get your **chat id**.
Keep both for Step 4.

## Step 2 — Copy the project to the server
From YOUR Mac's Terminal (one command; replace SERVER_IP and user):
```
scp -r "$HOME/Desktop/CLAUDE/OPTIONS STRATEGIES" ubuntu@SERVER_IP:~/options
```
(Your secrets aren't in the folder yet, so nothing sensitive is copied.)

## Step 3 — Log in and run setup
```
ssh ubuntu@SERVER_IP
cd ~/options
bash deploy/setup_vps.sh
```
This installs Python, dependencies, creates data folders, and installs the cron schedule
(entry, monitor, tracker, daily heartbeat) automatically.

## Step 4 — Add your keys on the server
```
nano ~/options/bot/.env
```
Fill in (from .env.example):
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (Step 1)
- `DELTA_API_KEY` / `DELTA_API_SECRET` — **read-only** keys from your Delta India account
- `DRY_RUN=false`   ← so it actually sends Telegram (leave `true` to test silently first)
- `COINGLASS_API_KEY` — leave blank (your plan doesn't include the heatmap; desk falls back safely)
Save: Ctrl+O, Enter, Ctrl+X.

## Step 5 — Test once, then let cron run it
```
cd ~/options/bot && python3 run_desk.py --mode entry
```
You should get a Telegram signal within seconds. Then:
```
python3 heartbeat.py     # should send the daily digest
crontab -l               # confirm the 4 scheduled jobs are installed
```
From now on it runs itself: daily entry signal, adjustment alerts while positions are open,
nightly settlement, and a daily "desk alive" message.

## Step 6 (optional) — See the dashboard from anywhere
```
cd ~/options && python3 -m http.server 8080
```
Open `http://SERVER_IP:8080/web/dashboard.html`. **Security:** if you expose it, put it behind
a firewall rule limited to your IP, or a password — don't leave it open to the whole internet.

## Daily message & health
- `heartbeat.py` sends one digest a day (alive + signals + open positions + best strategy).
- **If the daily message stops arriving, your VPS is down** — that silence is the alert. Log in
  and check `~/options/data/*.log`.

## Times
Cron is in **UTC**. IST = UTC + 5:30. The default entry is 03:30 UTC = **09:00 IST**. To change
when the daily trade fires, edit the entry line: `crontab -e`.

## Keeping it updated
When I change code, re-copy just the changed files (repeat Step 2) — your `.env` on the server
is untouched. Or use a private GitHub repo and `git pull` if you prefer.
```
```
