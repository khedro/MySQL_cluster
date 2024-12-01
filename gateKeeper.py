import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import paramiko
import subprocess
import requests
from main import get_public_ip, create_login_key_pair, verify_valid_credentials, prepare_ssh_key

#try this way to create security group for our GateKeeper
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
        Description='Security group for GateKeeper',
        VpcId=vpc_id
    )

    security_group_id = response_security_group['GroupId']

    #Allow all traffic to GateKeeper.
    ec2_client.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            {'IpProtocol': 'tcp',
             'FromPort': 80,
             'ToPort': 80,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': '-1',
             'FromPort': 0,
             'ToPort': 65535,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 22,
             'ToPort': 22,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
        ]
    )

    print(f"Created security group '{name}' with ID: {security_group_id}")
    return security_group_id
###
#First, we verify valid credentials::
verify_valid_credentials()

ec2 = boto3.client('ec2')

#create security group for the gatekeeper:
create_security_group(ec2, "sg_gateKeeper")

#get sec group id of sg_katekeeper to link with trusted host::
response = ec2.describe_security_groups(
    Filters=[{'Name': 'group-name', 'Values': ["sg_gateKeeper"]}]
)
gatekeeper_sg_id = response['SecurityGroups'][0]['GroupId']

#create a separate security group for the trusted host that only gets traffic from gatekeeper
security_group = ec2.create_security_group(
    GroupName='sg_trustedHost',
    Description='Security group for Trusted Host'
)

# Authorize inbound traffic from the Gatekeeper's security group to the Trusted Host
# NEED TO AUTHORIZE SSH FROM LOCAL SO I CAN RUN PARAMIKO !@!@
# Fetch public IP
your_ip = get_public_ip()

ec2.authorize_security_group_ingress(
    GroupId=security_group['GroupId'],
    IpPermissions=[
        # Allow FastAPI traffic from GateKeeper's security group
        {
            'IpProtocol': 'tcp',
            'FromPort': 5000,
            'ToPort': 5000,
            'UserIdGroupPairs': [{'GroupId': gatekeeper_sg_id}]
        },
        # Open up ephemeral ports ?
        {
            'IpProtocol': 'tcp',
            'FromPort': 1024,
            'ToPort': 65535,
            'UserIdGroupPairs': [{'GroupId': gatekeeper_sg_id}]
        },
        # Allow SSH access from your current public IP
        {
            'IpProtocol': 'tcp',
            'FromPort': 22,
            'ToPort': 22,
            'IpRanges': [{'CidrIp': f'{your_ip}/32'}]
        }
    ]
)

# Launch instances::
print('Creating key pair...')
ec2_client = boto3.resource('ec2')
create_login_key_pair(ec2_client)
prepare_ssh_key()

print('Creating GateKeeper instance...')
gatekeeper_instance = ec2.run_instances(
    ImageId='ami-0e86e20dae9224db8',  
    InstanceType='t2.large',
    KeyName='test-key-pair',
    SecurityGroupIds=['sg_gateKeeper'],
    MinCount=1,
    MaxCount=1,
    TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'GateKeeper'}]}]
)

print('Creating TrustedHost instance...')
trusted_host_instance = ec2.run_instances(
    ImageId='ami-0e86e20dae9224db8',  
    InstanceType='t2.large',
    KeyName='test-key-pair',
    SecurityGroupIds=['sg_trustedHost'],
    MinCount=1,
    MaxCount=1,
    TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'TrustedHost'}]}]
)

print('Done creating GateKeeper instances...')
