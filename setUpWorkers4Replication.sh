#!/bin/bash
#HAVE TO SCP cluster_config.json + ~/.ssh/test-key.pair before
cd ~
config_file="/etc/mysql/mysql.conf.d/mysqld.cnf"

# ADDED THIS !!!!
# Update bind-address in the configuration file
private_ip=$(hostname -I | awk '{print $1}')
sudo sed -i "s/^bind-address.*/bind-address = ${private_ip}/" $config_file

# Uncomment server-id line and change it to something different than the source
# Each replica must have a unique server_id::
server_id=$(echo $private_ip | awk -F '.' '{print $4}')

sudo sed -i "s|^# server-id.*|server-id = ${server_id}|" $config_file

# Uncomment log_bin line
sudo sed -i "s|^# log_bin|log_bin|" $config_file

# Uncomment binlog_do_db and replace include_database_name with 'sakila'
sudo sed -i "s|^# binlog_do_db.*|binlog_do_db = sakila|" $config_file

# add relay-log dir defining the dir of the replica’s relay log file to the end of the configuration file
echo "relay-log = /var/log/mysql/mysql-relay-bin.log" | sudo tee -a $config_file

# ??? Edit this too to debug error we're getting ???
sudo sed -i "s|^# max_allowed_packet.*|max_allowed_packet = 999M|" $config_file
# max_allowed_packet    = 64M

#restart to implement new configuration:
sudo systemctl restart mysql

#now start MySQL replication:
manager_ip=$(jq -r '.Manager' cluster_config.json)

#get replication info from manager to input source log file + position in setup::
sudo scp -o StrictHostKeyChecking=no -i test-key-pair.pem ubuntu@$manager_ip:/home/ubuntu/replication_info.txt ./
source replication_info.txt

#added two lines here
sudo mysql -u root --password='' <<EOF
CHANGE REPLICATION SOURCE TO
SOURCE_HOST="${manager_ip}",
SOURCE_USER='replica_user1',
SOURCE_PASSWORD='Password11!',
SOURCE_LOG_FILE="${source_log_file}",
SOURCE_LOG_POS=${source_log_pos};

CREATE USER 'root'@'%' IDENTIFIED BY 'Password11!';
GRANT ALL PRIVILEGES ON sakila.* TO 'root'@'%' WITH GRANT OPTION;

START REPLICA;
SHOW REPLICA STATUS\G;
EOF


