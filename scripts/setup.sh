#!/bin/bash
# Pandemic Digital Twin Simulator - Quick Setup Script

echo "=== Pandemic Digital Twin Simulator Setup ==="
echo ""

# Backend setup
echo "[1/4] Setting up Python backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt --quiet
echo "Backend dependencies installed."
deactivate
cd ..

# Frontend setup
echo "[2/4] Setting up React frontend..."
cd frontend
npm install --silent
echo "Frontend dependencies installed."
cd ..

# Copy env files
echo "[3/4] Copying environment files..."
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

echo "[4/4] Setup complete!"
echo ""
echo "To start the system:"
echo ""
echo "  Terminal 1 (Backend):"
echo "    cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    cd frontend && npm run dev"
echo ""
echo "  Dashboard: http://localhost:3000"
echo "  API Docs:  http://localhost:8000/api/docs"
