from fastapi import FastAPI, HTTPException
import mysql.connector
import json
import uvicorn
import requests
import subprocess

app = FastAPI()

# Get IP of the worker in question::import socket
worker_ip = subprocess.getoutput("hostname -I | awk '{print $1}'")

print(f"Worker ip defined as {worker_ip}")

DB_CONFIG = {
    "user": "root",
    "password": "Password11!", # NOTE:: Not best practice !! 
    "host": worker_ip,  # Localhost for the DB server on this instance
    "database": "sakila",
}

# Added this to make sure we can reach it::
@app.get("/test")
async def mic_check():
    return("mic check 1 2 mic check 1 2")

# Added this for pinging endpoint
@app.get("/ping")
async def ping():
    return {"status": "ok"}

# Manager can handle READ requests too if they're direct !!
# TEST LIKE THIS:: curl -X GET "http://<INSTANCE_IP>:5000/read"
@app.get("/read")
async def read_from_db():
    conn = None  # Initialize conn to None
    try:
        # Connect to the MySQL database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Example: Read all rows from the `actor` table
        #query = "SELECT * FROM actor;"
        #CHANGED to select only last actor
        query = "SELECT * FROM actor ORDER BY actor_id DESC LIMIT 1;" 
        cursor.execute(query)
        rows = cursor.fetchall()

        # Return the data as a response
        return {"status": "success", "data": rows}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"MySQL error: {err}")
    finally:
        # Clean up resources
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5000)