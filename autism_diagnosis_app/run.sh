#!/bin/bash

# Activate venv
source venv/bin/activate

# Start Backend
echo "Starting server at http://localhost:8000"
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
