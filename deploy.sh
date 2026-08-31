#!/bin/bash
set -e

echo "=== Deploying AI Recruitment Bot ==="

# Check if docker is installed
if command -v docker &> /dev/null; then
    echo "Using Docker Compose deployment..."
    docker compose down || true
    docker compose build
    docker compose up -d
    echo "✓ Bot deployed and running 24/7 in Docker container!"
    docker compose logs -f
else
    echo "Docker not found, setting up Python virtualenv..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    # Setup systemd service
    SERVICE_FILE="/etc/systemd/system/recruitment_bot.service"
    CURRENT_DIR=$(pwd)
    
    echo "Creating systemd service at $SERVICE_FILE..."
    sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=AI Recruitment Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable recruitment_bot
    sudo systemctl restart recruitment_bot
    echo "✓ Bot service started via systemd!"
    sudo systemctl status recruitment_bot
fi
