#!/bin/bash

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Initialize database
sudo -u postgres psql -f init_db.sql

# Run migrations
alembic upgrade head

# Create necessary directories
mkdir -p src/static/{img,css,js}
mkdir -p src/templates/components/modals

# Set up udev rules for modems
sudo cp 99-usb-modems.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger 