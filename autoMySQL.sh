#!/usr/bin/expect -f

spawn sudo mysql_secure_installation
expect -re "Press y\\|Y for Yes, any other key for No:" { send "y\r" }
expect -re "Please enter 0 = LOW, 1 = MEDIUM and 2 = STRONG:" { send "2\r" }
expect -re "Remove anonymous users\\? .*:" { send "n\r" }
expect -re "Change the password for root\\? .*:" { send "y\r" }
expect -re "Disallow root login remotely\\? .*:" { send "y\r" }
expect -re "Remove test database and access to it\\? .*:" { send "y\r" }
expect -re "Reload privilege tables now\\? .*:" { send "y\r" }
expect eof
