from fastapi import FastAPI, HTTPException, Request, Body
import httpx
import json
import uvicorn

app = FastAPI()

# HAVE TO REUPLOAD THESE FILES TO THE TRUSTED HOST + GATEKEEPER
# Load configuration
with open("cluster_config.json", "r") as f:
    data = json.load(f)

# Private IPs of the Proxy and Gatekeeper
proxy_ip = data["Proxy"]
gatekeeper_ip = data["GateKeeper"]

#add this as a check::
@app.get("/")
async def homePage():
    return (
        "It works."
    )

@app.post("/process")
async def process_request(request: Request, request_body: dict = Body(...)):
    # Ensure the request comes from the Gatekeeper
    if request.client.host != gatekeeper_ip:
        raise HTTPException(status_code=403, detail="Unauthorized source")

    # Extract action and proxy from the request body
    action = request_body.get("action")
    proxy = request_body.get("proxy")

    # Validate the combination of action and proxy
    if action == "read" and proxy in {"direct_read", "random", "customized"}:
        proxy_endpoint = f"http://{proxy_ip}:5000/{proxy}"
    elif action == "write" and proxy == "direct_write":
        proxy_endpoint = f"http://{proxy_ip}:5000/{proxy}"
    else:
        raise HTTPException(status_code=400, detail="Invalid action-proxy combination")

    print(f'Sending to proxy endpoint: {proxy_endpoint}')
    # Forward the request to the determined proxy endpoint
    async with httpx.AsyncClient() as client:
        try:
            if action == "read":
                # GET requests for read operations
                response = await client.get(proxy_endpoint)
            else:
                # POST requests for write operations
                response = await client.post(proxy_endpoint, json=request_body)
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Proxy unreachable")

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=5000)
