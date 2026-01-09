from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from sqlmodel import SQLModel, create_engine, Session, select
from typing import List, Dict, Any
import json

from .models import Ambulance, Emergency

app = FastAPI()
engine = create_engine("sqlite:///./db.sqlite", echo=False)
SQLModel.metadata.create_all(engine)

class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        data = json.dumps(message)
        for ws in list(self.active):
            try:
                await ws.send_text(data)
            except Exception:
                self.disconnect(ws)

manager = ConnectionManager()

@app.post('/api/ambulances')
async def create_or_update_ambulance(a: Ambulance):
    with Session(engine) as session:
        existing = session.get(Ambulance, a.id)
        if existing:
            existing.lat = a.lat
            existing.lon = a.lon
            existing.status = a.status
            existing.call_sign = a.call_sign
            session.add(existing)
            session.commit()
            ambulance = existing
        else:
            session.add(a)
            session.commit()
            ambulance = a

    await manager.broadcast({"type": "ambulance:update", "ambulance": ambulance.dict()})
    return ambulance

@app.get('/api/ambulances')
def list_ambulances():
    with Session(engine) as session:
        return session.exec(select(Ambulance)).all()

@app.post('/api/emergencies')
async def create_emergency(e: Emergency):
    with Session(engine) as session:
        session.add(e)
        session.commit()
        session.refresh(e)

    await manager.broadcast({"type": "emergency:update", "emergency": e.dict()})
    return e

@app.get('/api/emergencies')
def list_emergencies():
    with Session(engine) as session:
        return session.exec(select(Emergency)).all()

@app.post('/api/emergencies/{emergency_id}/assign')
async def assign(emergency_id: str, payload: Dict[str, Any]):
    ambulance_id = payload.get('ambulance_id')
    with Session(engine) as session:
        em = session.get(Emergency, emergency_id)
        if not em:
            raise HTTPException(status_code=404, detail='Emergency not found')
        em.assigned_ambulance_id = ambulance_id
        em.status = 'assigned'
        session.add(em)
        session.commit()
        session.refresh(em)

    await manager.broadcast({"type": "assignment", "emergency": em.dict()})
    return em

@app.websocket('/ws')
async def ws_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            text = await ws.receive_text()
            data = json.loads(text)
            typ = data.get('type')

            if typ == 'ambulance:update':
                amb = data.get('ambulance')
                if amb:
                    with Session(engine) as session:
                        existing = session.get(Ambulance, amb.get('id'))
                        if existing:
                            existing.lat = amb.get('lat')
                            existing.lon = amb.get('lon')
                            existing.status = amb.get('status')
                            existing.call_sign = amb.get('call_sign', existing.call_sign)
                            session.add(existing)
                            session.commit()
                            session.refresh(existing)
                            out = existing.dict()
                        else:
                            new = Ambulance(**amb)
                            session.add(new)
                            session.commit()
                            session.refresh(new)
                            out = new.dict()
                    await manager.broadcast({"type": "ambulance:update", "ambulance": out})

            elif typ == 'emergency:update':
                em = data.get('emergency')
                if em:
                    with Session(engine) as session:
                        existing = session.get(Emergency, em.get('id'))
                        if existing:
                            for k, v in em.items():
                                setattr(existing, k, v)
                            session.add(existing)
                            session.commit()
                            session.refresh(existing)
                            out = existing.dict()
                        else:
                            new = Emergency(**em)
                            session.add(new)
                            session.commit()
                            session.refresh(new)
                            out = new.dict()
                    await manager.broadcast({"type": "emergency:update", "emergency": out})

            elif typ == 'assignment':
                emergency_id = data.get('emergency_id')
                ambulance_id = data.get('ambulance_id')
                with Session(engine) as session:
                    em = session.get(Emergency, emergency_id)
                    if em:
                        em.assigned_ambulance_id = ambulance_id
                        em.status = 'assigned'
                        session.add(em)
                        session.commit()
                        session.refresh(em)
                        await manager.broadcast({"type": "assignment", "emergency": em.dict()})

    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)
