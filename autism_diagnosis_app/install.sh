#!/bin/bash

echo "Starting installation..."

# Update system
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv libgl1-mesa-glx

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r backend/requirements.txt

echo "Installation complete."
echo "To run the application, execute: ./run.sh"
