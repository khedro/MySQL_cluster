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
#python3 benchmark.py

#identify IP of GateKeeper and send requests to it in parallel::
ip_gate=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=GateKeeper" "Name=instance-state-name,Values=running" --query "Reservations[*].Instances[*].PublicIpAddress" --output text)

#send 1000 via direct_write proxy
{ time seq 1000 | parallel --max-args 0 --jobs 10 "curl -X POST http://${ip_gate}:5000/validate -H \"Content-Type: application/json\" -d '{\"action\": \"write\", \"proxy\": \"direct_write\", \"first_name\": \"Omar\", \"last_name\": \"Khedr\"}'" ;} 2>&1 | tee benchmark_direct_write.log

#send 1000 via direct_read
{ time seq 1000 | parallel --max-args 0 --jobs 10 "curl -X POST http://${ip_gate}:5000/validate -H \"Content-Type: application/json\" -d '{\"action\": \"read\", \"proxy\": \"direct_read\"}'" ; } 2>&1 | tee benchmark_direct_read.log

#send 1000 via random proxy 
{ time seq 1000 | parallel --max-args 0 --jobs 10 "curl -X POST http://${ip_gate}:5000/validate -H \"Content-Type: application/json\" -d '{\"action\": \"read\", \"proxy\": \"random\"}'" ; } 2>&1 | tee benchmark_random.log

#send 1000 via customize proxy
{ time seq 1000 | parallel --max-args 0 --jobs 10 "curl -X POST http://${ip_gate}:5000/validate -H \"Content-Type: application/json\" -d '{\"action\": \"read\", \"proxy\": \"customized\"}'" ; } 2>&1 | tee benchmark_customized.log

#download logs from Manager + Worker1 + Worker2 to show it works::
ips=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=Manager,Worker1,Worker2" "Name=instance-state-name,Values=running" --query "Reservations[*].Instances[*].PublicIpAddress" --output text)

#save logs + actor table to our local dir::
for i in ${ips}; do
    sudo scp -i ~/.ssh/test-key-pair.pem -o StrictHostKeyChecking=no ubuntu@${i}:/home/ubuntu/*.log ${i}.log
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/test-key-pair.pem ubuntu@${i} "sudo mysqldump -u root --password='' sakila actor" > actor_table_${i}.sql
done

