Control Room MVP

This branch adds a minimal FastAPI backend with WebSocket support, a Leaflet-based frontend, and a simple simulator for ambulances.

Run backend:
  python -m venv venv
  source venv/bin/activate
  pip install -r backend/requirements.txt
  uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

Serve frontend (from repo root):
  cd frontend
  python -m http.server 8080
  Open http://localhost:8080

Run simulator:
  python tools/simulator.py --count 3 --interval 3 --ws ws://localhost:8000/ws
