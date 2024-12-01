from fastapi import FastAPI, HTTPException
import mysql.connector
import json
import uvicorn

app = FastAPI()

# Database connection details, IPs in JSON
with open("cluster_config.json", "r") as f:
    data = json.load(f)

manager_ip = data["Manager"]

DB_CONFIG = {
    "user": "root",
    "password": "Password11!", # NOTE:: Not best practice !! 
    "host": manager_ip,  # Localhost for the DB server on this instance
    "database": "sakila",
}

# Added this to make sure we can reach it::
@app.get("/test")
async def mic_check():
    return("mic check 1 2 mic check 1 2")

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
        query = "SELECT * FROM actor;"
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

# Endpoint to handle WRITE requests
# This is how im testing it for now::
# curl -X POST "http://54.159.139.56:5000/write" -H "Content-Type: application/json" -d '{"first_name": "Omar", "last_name": "Khedr"}'
@app.post("/write")
async def write_to_db(request_body: dict):
    conn = None  # Initialize conn to None to avoid referencing before assignment
    try:
        # Connect to the MySQL database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Insert a row into a table
        query = "INSERT INTO actor (first_name, last_name) VALUES (%s, %s);"
        values = (request_body["first_name"], request_body["last_name"])

        cursor.execute(query, values)
        conn.commit()

        # Return success response
        return {"status": "success", "rows_affected": cursor.rowcount}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"MySQL error: {err}")
    finally:
        # Ensure resources are cleaned up if conn is not None and was successfully created
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5000)
