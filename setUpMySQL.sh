#!/bin/bash
#from inside instance::
sudo apt-get update
yes | sudo apt-get install mysql-server

#automate this sequence w/ expect::
sudo apt-get install -y expect

#automate MySQL setup::
sudo expect autoMySQL.sh
#sequence: y 2 y n y y

#set up sakila DB::
sudo apt install unzip
unzip sakila-db.zip

#using this we enter the mysql standalone and run these from within
sudo mysql -u root --password='' <<EOF
SOURCE /home/ubuntu/sakila-db/sakila-schema.sql;
SOURCE /home/ubuntu/sakila-db/sakila-data.sql;
EOF

#run sysbench check::
sudo apt-get install sysbench -y

#run check::
sudo /usr/share/sysbench/oltp_read_only.lua --mysql-db=sakila --mysql-user="root" --mysql-password="" prepare

sudo /usr/share/sysbench/oltp_read_only.lua --mysql-db=sakila --mysql-user="root" --mysql-password="" run
