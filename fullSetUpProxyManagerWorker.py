#This script will be used to set up manager-subordinate replication between
#Manager and worker instances AND deploy the required FastAPI apps for the architecture::
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
import paramiko
import time
import shutil

def execute_commands_on_workers(ec2_client):
    instances = ec2_client.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )
    
    # Loop through all running instances
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_name = None
            if 'Tags' in instance:
                for tag in instance['Tags']:
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
            
            if instance_name not in ["Worker1", "Worker2"]:
                print(f"Skipping non Worker instance with IP {instance.get('PublicIpAddress')}")
                continue 
            
            ip_address = instance['PublicIpAddress']
            print(f'Connecting to instance {ip_address}...')
            ssh_key = paramiko.RSAKey.from_private_key_file('test-key-pair.pem')
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh_client.connect(hostname=ip_address, username='ubuntu', pkey=ssh_key)
                print(f'Connected to {ip_address}')
                
                # SFTP files into instance
                sftp = ssh_client.open_sftp()
                sftp.put('cluster_config.json', '/home/ubuntu/cluster_config.json')
                sftp.put('/home/robomar/.ssh/test-key-pair.pem', '/home/ubuntu/test-key-pair.pem')
                sftp.put('setUpWorkers4Replication.sh', '/home/ubuntu/setUpWorkers4Replication.sh')
                
                sftp.put('appWorkers.py', '/home/ubuntu/appWorkers.py')
                sftp.put('requirementsO.txt', '/home/ubuntu/requirementsO.txt')
                sftp.put('setUpWorkersApp.sh', '/home/ubuntu/setUpWorkersApp.sh')

                sftp.close()

                # Run commands
                stdin, stdout, stderr = ssh_client.exec_command('echo Hello from $(hostname)')
                print(stdout.read().decode())

                stdin, stdout, stderr = ssh_client.exec_command(
                    'bash setUpWorkers4Replication.sh; nohup bash setUpWorkersApp.sh &'
                )
                print(stdout.read().decode())
                print(stderr.read().decode())

            except Exception as e:
                print(f"Failed to connect or run commands on {ip_address}: {e}")
            finally:
                ssh_client.close()
                print(f'Disconnected from {ip_address}')

    print('Done executing commands on Workers.')

#Now for the manager::
def execute_commands_on_manager(ec2_client):
    instances = ec2_client.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )
    
    # Loop through all running instances
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_name = None
            if 'Tags' in instance:
                for tag in instance['Tags']:
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
            
            if instance_name != "Manager":
                print(f"Skipping non Manager instance with IP {instance.get('PublicIpAddress')}")
                continue  # Skip Proxy instance
            
            ip_address = instance['PublicIpAddress']
            print(f'Connecting to instance {ip_address}...')
            ssh_key = paramiko.RSAKey.from_private_key_file('test-key-pair.pem')
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh_client.connect(hostname=ip_address, username='ubuntu', pkey=ssh_key)
                print(f'Connected to {ip_address}')
                
                # SFTP files into instance
                sftp = ssh_client.open_sftp()
                
                sftp.put('cluster_config.json', '/home/ubuntu/cluster_config.json')
                #sftp.put('~/.ssh/test-key-pair.pem', '/home/ubuntu/test-key-pair.pem')
                sftp.put('setUpSource4Replication.sh', '/home/ubuntu/setUpSource4Replication.sh')

                sftp.put('requirementsO.txt', '/home/ubuntu/requirementsO.txt')
                sftp.put('appManager.py', '/home/ubuntu/appManager.py')
                sftp.put('setUpManagerApp.sh', '/home/ubuntu/setUpManagerApp.sh')
                sftp.close()

                # Run commands
                stdin, stdout, stderr = ssh_client.exec_command('echo Hello from $(hostname)')
                print(stdout.read().decode())

                stdin, stdout, stderr = ssh_client.exec_command(
                    'bash setUpSource4Replication.sh; nohup bash setUpManagerApp.sh &'
                )
                print(stdout.read().decode())
                print(stderr.read().decode())

            except Exception as e:
                print(f"Failed to connect or run commands on {ip_address}: {e}")
            finally:
                ssh_client.close()
                print(f'Disconnected from {ip_address}')

    print('Done executing commands on Manager.')

#Finally the proxy::
#Now for the manager::
def execute_commands_on_proxy(ec2_client):
    instances = ec2_client.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )
    
    # Loop through all running instances
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_name = None
            if 'Tags' in instance:
                for tag in instance['Tags']:
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
            
            if instance_name != "Proxy":
                print(f"Skipping non Proxy instance with IP {instance.get('PublicIpAddress')}")
                continue  # Skip Proxy instance
            
            ip_address = instance['PublicIpAddress']
            print(f'Connecting to instance {ip_address}...')
            ssh_key = paramiko.RSAKey.from_private_key_file('test-key-pair.pem')
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh_client.connect(hostname=ip_address, username='ubuntu', pkey=ssh_key)
                print(f'Connected to {ip_address}')
                
                # SFTP files into instance
                sftp = ssh_client.open_sftp()
                
                sftp.put('cluster_config.json', '/home/ubuntu/cluster_config.json')
                sftp.put('requirementsO.txt', '/home/ubuntu/requirementsO.txt')
                sftp.put('appProxy.py', '/home/ubuntu/appProxy.py')
                sftp.put('setUpProxyApp.sh', '/home/ubuntu/setUpProxyApp.sh')
                sftp.close()

                # Run commands
                stdin, stdout, stderr = ssh_client.exec_command('echo Hello from $(hostname)')
                print(stdout.read().decode())

                stdin, stdout, stderr = ssh_client.exec_command(
                    'nohup bash setUpProxyApp.sh &'
                )
                print(stdout.read().decode())
                print(stderr.read().decode())

            except Exception as e:
                print(f"Failed to connect or run commands on {ip_address}: {e}")
            finally:
                ssh_client.close()
                print(f'Disconnected from {ip_address}')

    print('Done executing commands on Proxy.')

#Execute::
ec2 = boto3.client('ec2')

#execute on manager first::
execute_commands_on_manager(ec2)

execute_commands_on_workers(ec2)

execute_commands_on_proxy(ec2)
