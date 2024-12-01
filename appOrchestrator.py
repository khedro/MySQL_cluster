from flask import Flask , request , jsonify
import threading
import json
import time
import requests
import boto3
import logging

app = Flask(__name__)
lock = threading.Lock()
#request_queue = []

#HERE HERE HERE
def send_request_to_container(container_id, container_info, incoming_request_data):
    ip = container_info["ip"]
    port = container_info["port"]

    #logging.info("sending request to container .. should see a message after, otherwise there's an error here")
    try:
        response = requests.post(f"http://{ip}:{port}/run_model", json=incoming_request_data)
        #logging.info(f"response for post is {response}")
        if response.status_code == 200:
            time.sleep(2)
            logging.info(f"Response from {container_id}: {response.json()}") #changed from response.json
            #update status back to free after 5 seconds
            #time.sleep(2)
            update_container_status(container_id, "free")
            # logging.info(f"container {container_id} updated to free")
            return True
        else:
            logging.info(f"Failed to send request to {container_id}")
            return False
    except requests.exceptions.RequestException as e:
        logging.info(f"Error sending request to {container_id}: {e}")
        return False

#removed lock in this function, we were already locking in process_request::
def update_container_status(container_id, status):
    #logging.info("updating container status")
    #logging.info("locking + opening test.json") #GOOD
    with open("test.json", "r") as f:
        data = json.load(f)
    data[container_id]["status"] = status
    with open("test.json", "w") as f:
        logging.info(f"Changing status to {status}")
        json.dump(data, f)

#list to append jobs to::
#added if/else here !@!
request_queue = [] 
def process_request(incoming_request_data):
    global request_queue

    if bool(request_queue) is False:
        while lock:
            with open("test.json", "r") as f:
                data = json.load(f)
            free_container = None

            #print from orchestrator::
            logging.info('printing json from orchstrator')
            logging.info(data)

            for container_id, container_info in data.items():
                if container_info["status"] == "free":
                    free_container = container_id
                    break
            if free_container:
                logging.info('sending request to free container ..')
                update_container_status(free_container, "busy")
                send_request_to_container(free_container, data[free_container], incoming_request_data)
            else:
                logging.info('all containers are full, adding to queue ..')
                request_queue.append(incoming_request_data)
                
    else:
        while bool(request_queue) is True:
            #2 seconds is way too little, try 10
            time.sleep(2)
            logging.info('seeing if there are any free containers ..')

            #removed lock here
            with open("test.json", "r") as f:
                data = json.load(f)
            free_container = None

            for container_id, container_info in data.items():
                if container_info["status"] == "free":
                    free_container = container_id
                    break
            
            #added with lock here
            if free_container:
                with lock:
                    logging.info('container has opened up ! Directing request to newly opened container')
                    update_container_status(free_container, "busy")
                    #sending element at the top of the queue::
                    send_request_to_container(free_container, data[free_container], request_queue[0])
                    #remove first element, first come first serve::
                    request_queue.pop(0)
               
#added a route
@app.route('/')
def home():
    return "Welcome to the Flask app! Available routes: /new_request"
            
@app.route("/new_request", methods=["POST"])
def new_request():
    #adding logging::
    #Try this if current method doesnt work
    #logging.basicConfig(level=logging.DEBUG)
    #logging = logging.getLogger(__name__)
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")
    
    incoming_request_data = request.json
    threading.Thread(target=process_request, args=(incoming_request_data,)).start()
    return jsonify({"message": "Request received and processing started."})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

