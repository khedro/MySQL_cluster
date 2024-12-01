#!/bin/bash
#script to set up source-replica replication pattern across instances::
#HAVE TO SCP cluster_config file before
#add rules to allow incoming traffic from other instances::
#NOTE:: using private IP here, if it doesnt work, change to public:
cd ~

proxy_ip=$(jq -r '.Proxy' cluster_config.json)
worker1_ip=$(jq -r '.Worker1' cluster_config.json)
worker2_ip=$(jq -r '.Worker2' cluster_config.json)

sudo ufw allow from $proxy_ip to any port 3306
sudo ufw allow from $worker1_ip to any port 3306
sudo ufw allow from $worker2_ip to any port 3306

#edit the mysqld.cnf file to allow for replication::
manager_ip=$(jq -r '.Manager' cluster_config.json)
config_file="/etc/mysql/mysql.conf.d/mysqld.cnf"

# Update bind-address in the configuration file
sudo sed -i "s/^bind-address.*/bind-address = ${manager_ip}/" $config_file

# Uncomment server-id line
sudo sed -i "s/^# server-id/server-id/" $config_file

# Uncomment log_bin line
sudo sed -i "s|^# log_bin|log_bin|" $config_file

# Uncomment binlog_do_db and replace include_database_name with 'sakila'
sudo sed -i "s|^# binlog_do_db.*|binlog_do_db = sakila|" $config_file

# ??? Edit this too to debug error we're getting ???
sudo sed -i "s|^# max_allowed_packet.*|max_allowed_packet = 999M|" $config_file
# max_allowed_packet    = 64M

# Restart MySQL service::
sudo systemctl restart mysql

# run this from within MySQL shell of source::
#using this we enter the mysql standalone and run these from within
#changed USER to be replica_user1 for both to facilitate auto setup::
#Added two separated lines to allow access from proxy:
# CREATE USER 'proxy'@"${proxy_ip}" IDENTIFIED WITH mysql_native_password BY 'Password11!';
# GRANT ALL PRIVILEGES ON sakila.* TO  'proxy'@"${proxy_ip}" WITH GRANT OPTION;
# This is how it was before ^^, but instead added the root part, and is now working
sudo mysql -u root --password='' <<EOF
CREATE USER 'replica_user1'@"${worker1_ip}" IDENTIFIED WITH mysql_native_password BY 'Password11!';
CREATE USER 'replica_user1'@"${worker2_ip}" IDENTIFIED WITH mysql_native_password BY 'Password11!';
GRANT REPLICATION SLAVE ON *.* TO 'replica_user1'@"${worker1_ip}";
GRANT REPLICATION SLAVE ON *.* TO 'replica_user1'@"${worker2_ip}";

CREATE USER 'root'@'%' IDENTIFIED BY 'Password11!';
GRANT ALL PRIVILEGES ON sakila.* TO 'root'@'%' WITH GRANT OPTION;

FLUSH PRIVILEGES;
FLUSH TABLES WITH READ LOCK;
SHOW MASTER STATUS;
UNLOCK TABLES;
EOF

#output source log file and position info for replication on workers, will be scp'd from the workers::
sudo mysql -u root --password='' -e "SHOW MASTER STATUS\G" | awk '/File:/ {print "source_log_file="$2} /Position:/ {print "source_log_pos="$2}' > replication_info.txt

##### Added UNLOCK TABLES command at the end, think this may be why it wasnt working earlier. 
#####SKIPPED DATA MIGRATION PART OF TUTORIAL GIVEN WE HAVE SAKILA ON ALL INSTANCES
#####IF REPLICATION DOESNT WORK GO BACK AND MIGRATE DATA

