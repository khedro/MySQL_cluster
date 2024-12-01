#!/bin/bash
sudo apt update
yes | sudo apt install python3-venv

python3 -m venv myenv

source myenv/bin/activate

pip install -r requirementsO.txt

#setup IPtables::
gateKeeper_ip=$(jq -r '.GateKeeper' cluster_config.json)
proxy_ip=$(jq -r '.Proxy' cluster_config.json)

###INPUT RULES::
#Allow traffic from GateKeeper IP only on port 5000
sudo iptables -A INPUT -p tcp -s ${gateKeeper_ip} --dport 5000 -j ACCEPT

#allow ssh from your local ip ?
#your_ip=$(curl http://checkip.amazonaws.com)
#sudo iptables -A INPUT -p tcp -s ${your_ip} --dport 22 -j ACCEPT
sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

#Drop all other incoming traffic
sudo iptables -P INPUT DROP

###OUTPUT RULES::
#Allow traffic to proxy on port 5000
sudo iptables -A OUTPUT -p tcp -d ${proxy_ip} --dport 5000 -j ACCEPT

#Allow established/related traffic e.g. responses to outgoing requests::
sudo iptables -A OUTPUT -m state --state RELATED,ESTABLISHED -j ACCEPT

#Drop all other outgoing traffic
sudo iptables -P OUTPUT DROP

#print new iptables rules::
sudo iptables -L

nohup python3 appTrustedHost.py > TrustedHost.log 2>&1 &

