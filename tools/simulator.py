#!/usr/bin/env python3
import asyncio
import argparse
import json
import random
import uuid
from websockets import connect

async def run(count, interval, ws_url):
    # create initial ambulances
    ambulances = []
    for i in range(count):
        aid = f'A{i+1}'
        lat = random.uniform(-0.1, 0.1) + (i * 0.01)
        lon = random.uniform(36.7, 36.9)
        ambulances.append({'id': aid, 'call_sign': f'Amb-{aid}', 'lat': lat, 'lon': lon, 'status': 'available'})

    async with connect(ws_url) as websocket:
        print('Simulator connected to', ws_url)
        while True:
            for a in ambulances:
                # random small move
                a['lat'] += random.uniform(-0.0005, 0.0005)
                a['lon'] += random.uniform(-0.0005, 0.0005)
                # random status change
                if random.random() < 0.05:
                    a['status'] = random.choice(['available','enroute','on_scene','transporting'])
                msg = {'type': 'ambulance:update', 'ambulance': a}
                await websocket.send(json.dumps(msg))
                print('sent', msg)
            await asyncio.sleep(interval)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--count', type=int, default=3)
    p.add_argument('--interval', type=float, default=3.0)
    p.add_argument('--ws', default='ws://localhost:8000/ws')
    args = p.parse_args()
    asyncio.run(run(args.count, args.interval, args.ws))
