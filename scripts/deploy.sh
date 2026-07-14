#!/bin/bash
set -e

echo "==== Starting web-scraper deploy.sh ===="

cd /opt/web-scraper-boilerplate

echo "Activating virtualenv..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Restarting Flask..."
pkill -f "flask run.*5001" || true
sleep 2

rm -f flask.log

export FLASK_APP=app.py
nohup flask run --host=0.0.0.0 --port=5001 > flask.log 2>&1 &

echo "✅ Deployment complete!"
