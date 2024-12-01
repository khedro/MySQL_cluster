#remember to pip install fastapi uvicorn httpx in instance::
from fastapi import FastAPI, HTTPException
import httpx
import random
import asyncio
import time
import json
import uvicorn

app = FastAPI()

# Database connection details, IPs in JSON
with open("cluster_config.json", "r") as f:
    data = json.load(f)

#Beware these are private IPs::
manager_ip = data["Manager"]
worker1_ip = data["Worker1"]
worker2_ip = data["Worker2"]

# Define MySQL nodes
nodes = {
    "manager": f"http://{manager_ip}:5000",
    "workers": [f"http://{worker1_ip}:5000", f"http://{worker2_ip}:5000"]
}

# Direct hit: forward to the manager node
@app.post("/direct_write")
async def direct_hit(request_body: dict):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{nodes['manager']}/write", json=request_body)
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Manager node unreachable")
        
@app.get("/direct_read")
async def direct_hit_read():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{nodes['manager']}/read")
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Manager node unreachable")

# Random: forward to a random worker node
@app.get("/random")
async def random_hit():
    worker_node = random.choice(nodes['workers'])
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{worker_node}/read")
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Random worker node unreachable")

# Customized: forward to the worker node with the lowest ping time
async def measure_ping(node_url):
    start_time = time.time()
    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"{node_url}/ping", timeout=2)
            return time.time() - start_time
    except httpx.RequestError:
        return float('inf')

@app.get("/customized")
async def customized_hit():
    ping_times = await asyncio.gather(*(measure_ping(node) for node in nodes['workers']))
    best_node = nodes['workers'][ping_times.index(min(ping_times))]
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{best_node}/read")
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Best worker node unreachable")

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5000)