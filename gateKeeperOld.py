import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
import paramiko
import  subprocess
import time

def get_security_groupID(ec2_client):
    try:
        group_name = 'LOG8415Secgroup'
        response = ec2_client.describe_security_groups(
            Filters=[
                dict(Name='group-name', Values=[group_name])
            ]
        )
        group_id = response['SecurityGroups'][0]['GroupId']
        return group_id
    except ClientError as e:
        print(e)

def create_GateKeeper(ec2_client,secGroupId):
    """"
    Create one large instance to be used as the GateKeeper
    The Fast Api app will be deployed through paramiko from setUpGateKeeper.sh
    """
    try:
        response = ec2_client.create_instances(ImageId='ami-0e86e20dae9224db8', MaxCount=1, InstanceType = 't2.large',
                                    MinCount=1, KeyName='test-key-pair',TagSpecifications=[  {'ResourceType': 'instance','Tags': [  {'Key': 'Name',
                    'Value': 'GateKeeper'}]}],SecurityGroupIds=[secGroupId])
        print("Creating GateKeeper")
        return response[0]
    except ClientError as e:
        print(f"Error: {e}")

def create_TrustedHost(ec2_client,secGroupId):
    """"
    Create one large instance to be used as the Load Balancer
    The Fast Api app will be deployed through paramiko from setUpTrustedHost.sh
    """
    try:
        response = ec2_client.create_instances(ImageId='ami-0e86e20dae9224db8', MaxCount=1, InstanceType = 't2.large',
                                    MinCount=1, KeyName='test-key-pair',TagSpecifications=[  {'ResourceType': 'instance','Tags': [  {'Key': 'Name',
                    'Value': 'TrustedHost'}]}],SecurityGroupIds=[secGroupId])
        print("Creating Trusted Host")
        return response[0]
    except ClientError as e:
        print(f"Error: {e}")

#function to get DNS of instance by name::
def get_dns(ec2_client, name):
    filters = [
        {
            'Name': 'tag:Name',  
            'Values': [name] #['Orchestrator']   
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

#scp files to GateKeeper and run commands::
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
        #sftp.put('test.json', '/home/ubuntu/test.json') 
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
        #Changed to Edouards !!!
        sftp.put('appTrustedHost.py', '/home/ubuntu/appTrustedHost.py')  
        sftp.put('setUpTrustedHost.sh', '/home/ubuntu/setUpTrustedHost.sh') 
        sftp.put('requirementsO.txt', '/home/ubuntu/requirementsO.txt')  
        #sftp.put('test.json', '/home/ubuntu/test.json') 
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

if __name__ == '__main__':
    ec2_res = boto3.resource("ec2")
    ec2_client = boto3.client('ec2')

    sec_group = get_security_groupID(ec2_client)
    create_GateKeeper(ec2_res, sec_group)
    create_TrustedHost(ec2_res, sec_group)
    time.sleep(60)
    execute_commands_on_GateKeeper(ec2_client)
    execute_commands_on_TrustedHost(ec2_client)



