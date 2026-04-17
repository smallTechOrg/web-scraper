# Deployment Guide - Scraper Backend on GCP VM

This guide walks through deploying the Hashtag Local Backend Java application on a GCP Compute Engine VM instance.

## Prerequisites

- GCP VM instance provisioned: `staging-instance` in `us-central1-f` zone
- SSH access configured with gcloud CLI

---

## Step 1: SSH into the VM Instance


Prod
```bash
gcloud compute ssh --zone "us-central1-f" "staging-instance" --project "ai-agent-boilerplate0"
```

## Step 2: Update System and check python version

```bash
# Update package manager
sudo apt-get update
sudo apt-get upgrade -y

# Verify python version
python3 --version
```

---

## Step 3: Install Git and Clone the Repository


### Using SSH Keys

```bash
# Install Git as root user
sudo su
apt-get install -y git

# Generate SSH key on the VM
ssh-keygen -t ed25519 -C "admin@madhyamakist.com"
# Press Enter to accept default location, add passphrase if desired

# Display the public key
cat ~/.ssh/id_ed25519.pub

# Add this public key to GitHub:
# 1. Copy the output
# 2. Go to GitHub.com → Settings → SSH and GPG keys → New SSH key
# 3. Paste the key and save

# Test the connection
ssh -T git@github.com

# Clone the repository
sudo su
cd /opt
sudo git clone git@github.com:smallTechOrg/web-scraper-boilerplate
cd web-scraper-boilerplate
```

---

## Step 4: Create Venv and Playwright Binaries

**On VM:**

```bash
# Create Venv
apt install python3.12-venv
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Install pytorch with no cpu (part of easyocr)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
# Install easyocr
pip install easyocr

# for opencv, system dependency
sudo apt install libgl1


# Install playwright with system dependecies
pip install playwright
python -m playwright install --with-deps chromium

pip install -r requirements.txt

```

---

## Step 8: Run the Application

```bash
# If already running, stop current scraper
pkill -f "/opt/web-scraper-boilerplate"

export FLASK_APP=app.py
nohup flask run --host=0.0.0.0 --port=5001 > flask.log 2>&1 &
```
---

## Step 9: Verify the Application is Running

```bash
# Check application health endpoint
curl http://localhost:5001/api/health

# For exposes OpenAPI docs
curl http://localhost:5001/docs
```

---

## Step 10: Configure Firewall and Load Balancer

For production setup with load balancer integration, see [infrastructure.md](infrastructure.md) for complete instructions on:
- Firewall rules for health checks
- Instance group configuration
- Backend service setup
- Load balancer path routing for `/webscraperstaging/*`
- SSL/TLS configuration
- Monitoring and troubleshooting

**Quick verification after infrastructure setup:**

```bash
# Test application is accessible via load balancer
curl https://staging.api.smalltech.com/webscraperstaging/api/health
```

---


# VM Commands 

For memory
```
free | grep Mem | awk '{print $3/$2 * 100.0"%"}'
df -h
```