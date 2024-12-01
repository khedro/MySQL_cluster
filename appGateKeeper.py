from fastapi import FastAPI, HTTPException, Body
import httpx
import json
import uvicorn

app = FastAPI()

# Load configuration
with open("cluster_config.json", "r") as f:
    data = json.load(f)

# Private IP of the trusted host
trusted_host_ip = data["TrustedHost"]

@app.get("/")
async def homePage():
    return (
        "Hello! To use, requests must be sent to /validate :) "
        + 'You must specify an action ("read" or "write") '
        + 'And you must specify a proxy ("direct_read", "direct_write", "random", "customized")'
        + 'If you are sending write requests, you must specify a first_name and last_name, to write to the DB'
    )

#This is how you test: 
#curl -X POST http://54.90.124.113:5000/validate -H "Content-Type: application/json" -d '{"action": "read", "proxy": "direct_read"}'
#curl -X POST http://54.90.124.113:5000/validate -H "Content-Type: application/json" -d '{"action": "write", "proxy": "direct_write", "first_name": "Omar", "last_name": "Khedr"}'
#getting: {"detail":"Trusted host unreachable"}
# Validate requests here
def validate_request(request_body: dict):
    required_keys = {"action", "proxy"}
    if not isinstance(request_body, dict) or not required_keys.issubset(request_body.keys()):
        raise HTTPException(status_code=400, detail="Invalid request format")

    # Validation rules
    action = request_body["action"]
    proxy = request_body["proxy"]

    if action == "read" and proxy not in {"direct_read", "random", "customized"}:
        raise HTTPException(
            status_code=400, detail="Invalid proxy for 'read'. Allowed values: 'direct_read', 'random', 'customized'"
        )
    elif action == "write" and proxy != "direct_write":
        raise HTTPException(
            status_code=400, detail="Invalid proxy for 'write'. Allowed value: 'direct_write'"
        )
    elif action not in {"read", "write"}:
        raise HTTPException(status_code=400, detail="Invalid action. Allowed values: 'read', 'write'")

@app.post("/validate")
async def validate_and_forward(request_body: dict = Body(...)):
    # Validate and sanitize input
    validate_request(request_body)

    # Forward to trusted host
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"http://{trusted_host_ip}:5000/process", json=request_body)
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Trusted host unreachable")

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=5000)
