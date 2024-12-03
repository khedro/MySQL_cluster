#!/bin/bash
#run Pipeline::
#creating virtual environment and installing requirements::
python3 -m venv venv
source venv/bin/activate
sudo apt-get update
pip install -r requirements.txt

#create 2 gatekeeper instances
python3 gateKeeper.py

sleep 45
#create Manager + Workers + Proxy
python3 main.py

#added sleep here
sleep 45
#generate json with IPs of all instances to be scp'd to them via paramiko
python3 getJsono.py

#deploy FastAPI architecture on all instances::
sleep 45
#setUp FastAPI w/ Manager/Worker replication::
python3 fullSetUpProxyManagerWorker.py
#setUp FastAPI on gateKeeper instances + IPtables for TrustedHost::
python3 gateKeeperII.py

#benchmark the architecture::
python3 benchmark.py

#download results::
ips=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=Manager,Worker1,Worker2" "Name=instance-state-name,Values=running" --query "Reservations[*].Instances[*].PublicIpAddress" --output text)

#save logs + actor table to our local dir::
for i in ${ips}; do
    sudo scp -i ~/.ssh/test-key-pair.pem -o StrictHostKeyChecking=no ubuntu@${i}:/home/ubuntu/*.log ${i}.log
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/test-key-pair.pem ubuntu@${i} "sudo mysqldump -u root --password='' sakila actor" > actor_table_${i}.sql
done

