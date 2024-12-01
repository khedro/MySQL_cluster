import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
import paramiko
import time
import shutil
import requests

def verify_valid_credentials():
    try:
        sts_client = boto3.client('sts')
        sts_client.get_caller_identity()
        print("Valid credentials")
    except NoCredentialsError as e:
        print("No credentials found")
    except ClientError as e:
        print(f"Error: {e}")

#allow traffic from within security group and from your IP::
def get_public_ip():
    try:
        response = requests.get('http://checkip.amazonaws.com', timeout=5)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.text.strip()  # Remove any trailing newline
    except requests.RequestException as e:
        print(f"Failed to fetch public IP: {e}")
        return None

#function to get sec group ID by name::
def get_security_groupID(ec2_client, group_name):
    try:
        response = ec2_client.describe_security_groups(
            Filters=[
                dict(Name='group-name', Values=[group_name])
            ]
        )
        group_id = response['SecurityGroups'][0]['GroupId']
        return group_id
    except ClientError as e:
        print(e)

# get public IP
your_ip = get_public_ip()
def create_security_group(ec2_client, name):
        # Check if the security group already exists
        response = ec2_client.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [name]}]
        )
        if response['SecurityGroups']:
            print(f"Security group '{name}' already exists.")
            return response['SecurityGroups'][0]['GroupId']

        # Proceed to create the security group if it doesn't exist
        response_vpcs = ec2_client.describe_vpcs()
        vpc_id = response_vpcs.get('Vpcs', [{}])[0].get('VpcId', '')

        response_security_group = ec2_client.create_security_group(
            GroupName=name,
            Description='Security group for our instances',
            VpcId=vpc_id
        )

        security_group_id = response_security_group['GroupId']

        #get security group id of trusted host::
        ec2 = boto3.client('ec2')
        response = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': ["sg_trustedHost"]}]
            )
        trustedHost_sg_id = response['SecurityGroups'][0]['GroupId']

        ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                #allow SSH access from your IP
                {'IpProtocol': 'tcp',
                 'FromPort': 22,
                 'ToPort': 22,
                 'IpRanges': [{'CidrIp': f'{your_ip}/32'}]},
                 #allow SSH traffic within the group
                {'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'UserIdGroupPairs': [{'GroupId': security_group_id}]},
                 #allow FastAPI communication (port 5000) within group 
                {'IpProtocol': 'tcp',
                 'FromPort': 5000,
                 'ToPort': 5000,
                 'UserIdGroupPairs': [{'GroupId': security_group_id}]},
                 #allow MySQL comms on port 3306 between them
                 {'IpProtocol': 'tcp',
                 'FromPort': 3306,
                 'ToPort': 3306,
                 'UserIdGroupPairs': [{'GroupId': security_group_id}]},
                 #allow FastAPI traffic from trusted host
                {'IpProtocol': 'tcp',
                 'FromPort': 5000,
                 'ToPort': 5000,
                  'UserIdGroupPairs': [{'GroupId': trustedHost_sg_id}]},
            ])
        
def create_workers(ec2_client,secGroupId):
    try:
        ec2_client.create_instances(ImageId='ami-0e86e20dae9224db8', MaxCount=1, InstanceType = 't2.micro',
                                    MinCount=1, KeyName='test-key-pair',SecurityGroupIds=[secGroupId],
                                    TagSpecifications=[  {'ResourceType': 'instance','Tags': [  {'Key': 'Name',
                    'Value': 'Worker1'}]}])
        
        ec2_client.create_instances(ImageId='ami-0e86e20dae9224db8', MaxCount=1, InstanceType = 't2.micro',
                                    MinCount=1, KeyName='test-key-pair',SecurityGroupIds=[secGroupId],
                                    TagSpecifications=[  {'ResourceType': 'instance','Tags': [  {'Key': 'Name',
                    'Value': 'Worker2'}]}])
        
        print("Creating 2 t2.micros as Workers")
    except ClientError as e:
        print(f"Error: {e}")

#make one for the cluster manager
def create_manager(ec2_client,secGroupId):
    try:
        ec2_client.create_instances(ImageId='ami-0e86e20dae9224db8', MaxCount=1, InstanceType = 't2.micro',
                                    MinCount=1, KeyName='test-key-pair',SecurityGroupIds=[secGroupId],
                                    TagSpecifications=[  {'ResourceType': 'instance','Tags': [  {'Key': 'Name',
                    'Value': 'Manager'}]}])
        print("Creating 1 t2.micro for the Manager")
    except ClientError as e:
        print(f"Error: {e}")

#and one for the proxy:
def create_proxy(ec2_client,secGroupId):
    try:
        ec2_client.create_instances(ImageId='ami-0e86e20dae9224db8', MaxCount=1, InstanceType = 't2.large',
                                    MinCount=1, KeyName='test-key-pair',SecurityGroupIds=[secGroupId],
                                    TagSpecifications=[  {'ResourceType': 'instance','Tags': [  {'Key': 'Name',
                    'Value': 'Proxy'}]}])
        print("Creating 1 t2.large for the Proxy")
    except ClientError as e:
        print(f"Error: {e}")

def create_login_key_pair(ec2_client):
    key_pair = ec2_client.create_key_pair(KeyName='test-key-pair', KeyType='rsa')
    print("Creating a key-pair to connect to the instances")
    with open('test-key-pair.pem', 'w') as file:
        file.write(key_pair.key_material)
    os.chmod('test-key-pair.pem', 0o444)

#added function to change permissions for keypair::
def prepare_ssh_key():
    # Define source and destination paths
    source_key = 'test-key-pair.pem'
    destination_dir = os.path.expanduser('~/.ssh/')
    destination_key = os.path.join(destination_dir, 'test-key-pair.pem')

    # Copy key pair to ~/.ssh/ directory
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
    shutil.copy(source_key, destination_key)
    print(f'Copied key pair to {destination_key}')

    # Set permissions for the key
    os.chmod(destination_key, 0o400)
    print(f'Set permissions for {destination_key}')

def execute_commands_on_all_ec2_instances(ec2_client):
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
            
            #Changed this part bc it was running commands on all instances !@!
            if instance_name not in ["Manager", "Worker1", "Worker2"]:
                print(f"Skipping instance with IP {instance.get('PublicIpAddress')}")
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
                sftp.put('sakila-db.zip', '/home/ubuntu/sakila-db.zip')
                sftp.put('setUpMySQL.sh', '/home/ubuntu/setUpMySQL.sh')
                sftp.put('autoMySQL.sh', '/home/ubuntu/autoMySQL.sh')
                sftp.close()

                # Run commands
                stdin, stdout, stderr = ssh_client.exec_command('echo Hello from $(hostname)')
                print(stdout.read().decode())

                stdin, stdout, stderr = ssh_client.exec_command(
                    'nohup bash setUpMySQL.sh &'
                )
                print(stdout.read().decode())
                print(stderr.read().decode())

            except Exception as e:
                print(f"Failed to connect or run commands on {ip_address}: {e}")
            finally:
                ssh_client.close()
                print(f'Disconnected from {ip_address}')

    print('Done setting up MySQL and Sakila on Manager + Workers.')

#execute::
if __name__ == "__main__":
    ec2_client = boto3.resource('ec2')
    ec2 = boto3.client('ec2')
    #verify_valid_credentials()
    create_security_group(ec2,'LOG8415Secgroup')
    secGroup_id = get_security_groupID(ec2, 'LOG8415Secgroup')
    #create_login_key_pair(ec2_client)

    #create the instances here::
    create_workers(ec2_client,secGroup_id)
    create_manager(ec2_client,secGroup_id)
    create_proxy(ec2_client,secGroup_id)

    #already prepared ssh key in gatekeeper scripts::
    #prepare_ssh_key()
    time.sleep(60) #have to sleep for a little to wait for the instances to be ready

    #set up MySQL on all of them EXCEPT the proxy::
    execute_commands_on_all_ec2_instances(ec2)


