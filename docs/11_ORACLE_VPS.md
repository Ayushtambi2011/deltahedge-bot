# 11 — Oracle Cloud (Always Free) Deploy — step by step

Goal: run the desk 24/7 on a free Oracle server so it works with your laptop off.
Go ONE phase at a time. If a step errors, stop and note the exact message.

---
## PHASE 1 — Create the free server (in Oracle's website)
1. Go to **cloud.oracle.com** → "Sign up for free". Use your email + phone. A card is required
   for identity verification only — **Always Free resources are not charged.**
2. **Home region:** pick an India region (e.g. **India South (Hyderabad)** or **India West (Mumbai)**).
   You cannot change this later, so choose India.
3. After login, open the menu (☰) → **Compute → Instances → Create instance**.
4. Set these:
   - **Name:** deltahedge
   - **Image:** click "Edit" → **Canonical Ubuntu 22.04**
   - **Shape:** click "Edit" → Ampere is ARM (often "out of capacity"). Instead choose
     **VM.Standard.E2.1.Micro** (AMD) — marked "Always Free eligible", and reliably available.
   - **Networking:** leave default (it creates a VCN and a **public IP** — make sure
     "Assign a public IPv4 address" is Yes).
   - **SSH keys:** choose **"Generate a key pair for me"** → click **Download private key**
     (and public key). Save the private key file — you need it to log in.
5. Click **Create**. Wait ~1 min until state = **Running**.
6. Copy the **Public IP address** shown on the instance page.

**Report back:** the Public IP, and confirm you downloaded the private key file.

---
## PHASE 2 — Log in and deploy (from YOUR Mac Terminal) — given after Phase 1
```
# 2a. protect the key (replace path with where the key downloaded, e.g. ~/Downloads/ssh-key-*.key)
chmod 400 ~/Downloads/ssh-key-*.key

# 2b. copy the project up (replace KEY and IP)
scp -i ~/Downloads/ssh-key-*.key -r "$HOME/Desktop/CLAUDE/OPTIONS STRATEGIES" ubuntu@PUBLIC_IP:~/options

# 2c. log in
ssh -i ~/Downloads/ssh-key-*.key ubuntu@PUBLIC_IP
```
Then ON THE SERVER:
```
cd ~/options
bash deploy/setup_vps.sh          # installs python, deps, and the cron schedule
nano bot/.env                     # paste Telegram + read-only Delta keys; set DRY_RUN=false
python3 bot/run_desk.py --mode entry   # test — you should get a Telegram signal
python3 bot/daily_brief.py             # test — you should get the morning brief
crontab -l                        # confirm 5 scheduled jobs
```

---
## PHASE 3 — (optional) See the dashboard from your browser
On the server: `cd ~/options && python3 -m http.server 8080`
In Oracle console: VCN → Security List → add Ingress rule for TCP 8080 from your IP only.
Open `http://PUBLIC_IP:8080/web/dashboard.html`. (Skip if you only want Telegram.)

## Schedule (already installed by setup_vps.sh) — all UTC
- 03:30 UTC (09:00 IST) entry signal · every 10 min monitor · 20:00 UTC settle
- **01:30 UTC (07:00 IST) daily brief** · 03:00 UTC heartbeat · Sun 21:00 learning review

## If the daily Telegram stops arriving
That silence = the server is down. Log in and check `~/options/data/*.log`.
