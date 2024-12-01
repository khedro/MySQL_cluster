import asyncio
import aiohttp
import time
import boto3
from gateKeeperII import get_dns

# Get GateKeeper public IP
ec2 = boto3.client('ec2')
gateKeeper_url = get_dns(ec2, "GateKeeper")
base_url = f"http://{gateKeeper_url}:5000/validate"

# Function to send a POST request to the validate endpoint
async def send_request(session, action, proxy, first_name=None, last_name=None):
    headers = {'Content-Type': 'application/json'}
    payload = {"action": action, "proxy": proxy}
    
    if action == "write":
        payload.update({"first_name": first_name, "last_name": last_name})

    try:
        async with session.post(base_url, json=payload, headers=headers) as response:
            status_code = response.status
            return status_code
    except Exception as e:
        return None

# Benchmarking function with proper throttling
async def benchmark_proxy(session, num_requests, action, proxy, first_name=None, last_name=None):
    print(f"Benchmarking {proxy} ({action}) with {num_requests} requests...")
    start_time = time.time()

    # Ensure only num_requests tasks are created and executed
    results = []
    for _ in range(num_requests):
        results.append(
            asyncio.create_task(
                send_request(session, action, proxy, first_name, last_name)
            )
        )

    # Wait for all tasks to complete
    await asyncio.gather(*results)

    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / num_requests

    print(f"Total time for {proxy} ({action}): {total_time:.2f} seconds")
    print(f"Average time per request: {avg_time:.4f} seconds\n")
    return total_time, avg_time

async def main():
    num_requests = 1000

    async with aiohttp.ClientSession() as session:
        # Start w/ write requests
        await benchmark_proxy(session, num_requests, action="write", proxy="direct_write", 
                              first_name="Omar", last_name="Khedr")

        # Benchmark read requests for each proxy
        read_proxies = ["direct_read", "random", "customized"]
        for proxy in read_proxies:
            await benchmark_proxy(session, num_requests, action="read", proxy=proxy)

if __name__ == "__main__":
    asyncio.run(main())
