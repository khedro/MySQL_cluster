#!/bin/bash
#run Pipeline::
#creating virtual environment and installing requirements::
#python3 -m venv venv
#source venv/bin/active
#pip install -r requirements.txt

#create 2 gatekeeper instances
python3 gateKeeper.py

#create Manager + Workers + Proxy
sleep 45
python3 main.py

#added sleep here
sleep 45
#generate json with IPs of all instances to be scp'd to them via paramiko
python3 getJsono.py

#deploy FastAPI architecture on all instances::
sleep 45
python3 fullSetUpProxyManagerWorker.py
python3 gateKeeperII.py

#benchmark the architecture::
python3 benchmark.py
