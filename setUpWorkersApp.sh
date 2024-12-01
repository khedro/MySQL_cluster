#!/bin/bash
sudo apt update
yes | sudo apt install python3.12-venv

python3 -m venv myenv

source myenv/bin/activate

pip install -r requirementsO.txt

nohup python3 appWorkers.py > Workers.log 2>&1 &