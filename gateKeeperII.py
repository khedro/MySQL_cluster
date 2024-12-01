import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
import paramiko
import time
import shutil
# Script to execute commands on gatekeeper instances::

#get DNS of any instance by name::
def get_dns(ec2_client, name):
    filters = [
        {
            'Name': 'tag:Name',  
            'Values': [name]  
        }
    ]

    # Describe instances that match the filters
    response = ec2_client.describe_instances(Filters=filters)

    # Access the instance details
    if not response['Reservations']:
        print('No instances with the specified tag were found.')
    else:
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                if instance['State']['Name'] == 'running':
                        return instance['PublicIpAddress']

#transfer files to these instances and run fastAPI apps on them::    
def execute_commands_on_GateKeeper(ec2_client):

    ip_address = get_dns(ec2_client, 'GateKeeper')
    print(f'Connecting to GateKeeper {ip_address}...')
    
    ssh_key = paramiko.RSAKey.from_private_key_file('test-key-pair.pem')
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh_client.connect(hostname=ip_address, username='ubuntu', pkey=ssh_key)
        print(f'Connected to GateKeeper')
        
        # sftp files into the instance 
        sftp = ssh_client.open_sftp()

        sftp.put('appGateKeeper.py', '/home/ubuntu/appGateKeeper.py')  
        sftp.put('setUpGateKeeper.sh', '/home/ubuntu/setUpGateKeeper.sh') 
        sftp.put('requirementsO.txt', '/home/ubuntu/requirementsO.txt')  
        sftp.put('cluster_config.json', '/home/ubuntu/cluster_config.json') 
        sftp.close() 

        # Run custom commands
        stdin, stdout, stderr = ssh_client.exec_command('bash setUpGateKeeper.sh &')
        print(stdout.read().decode())
        print(stderr.read().decode())

    except Exception as e:
        print(f"Failed to connect or run commands on GateKeeper: {e}")
    finally:
        ssh_client.close()
        print(f'Disconnected from {ip_address}')

    print('Done executing commands on the GateKeeper.')

#Do the same thing for the Trusted Host::
def execute_commands_on_TrustedHost(ec2_client):

    ip_address = get_dns(ec2_client, 'TrustedHost')
    print(f'Connecting to TrustedHost {ip_address}...')
    
    ssh_key = paramiko.RSAKey.from_private_key_file('test-key-pair.pem')
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh_client.connect(hostname=ip_address, username='ubuntu', pkey=ssh_key)
        print(f'Connected to TrustedHost')
        
        # sftp files into the instance 
        sftp = ssh_client.open_sftp()

        sftp.put('appTrustedHost.py', '/home/ubuntu/appTrustedHost.py')  
        sftp.put('setUpTrustedHost.sh', '/home/ubuntu/setUpTrustedHost.sh') 
        sftp.put('requirementsO.txt', '/home/ubuntu/requirementsO.txt')  
        sftp.put('cluster_config.json', '/home/ubuntu/cluster_config.json') 
        sftp.close() 

        # Run custom commands
        stdin, stdout, stderr = ssh_client.exec_command('bash setUpTrustedHost.sh &')
        print(stdout.read().decode())
        print(stderr.read().decode())

    except Exception as e:
        print(f"Failed to connect or run commands on Trusted Host: {e}")
    finally:
        ssh_client.close()
        print(f'Disconnected from {ip_address}')

    print('Done executing commands on the Trusted Host.')

#RUN
if __name__ == "__main__":
    ec2 = boto3.client('ec2')

    execute_commands_on_GateKeeper(ec2)
    execute_commands_on_TrustedHost(ec2)


