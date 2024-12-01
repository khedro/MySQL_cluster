import boto3
import json

REGION = "us-east-1"
roles = {"Manager": None, "Proxy": None, "Worker1": None, "Worker2": None, "GateKeeper": None, "TrustedHost": None}
ec2 = boto3.client('ec2', region_name=REGION)

def fetch_instance_ips():
    response = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            name_tag = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), None)
            print(f"Checking instance: {name_tag}")
            if name_tag in roles:
                print(f"Matched: {name_tag} -> {instance['PrivateIpAddress']}")
                roles[name_tag] = instance['PrivateIpAddress']
    return roles

if __name__ == "__main__":
    roles_with_ips = fetch_instance_ips()
    missing_roles = [role for role, ip in roles_with_ips.items() if ip is None]
    if missing_roles:
        print(f"Some roles are missing IPs: {missing_roles}")
    else:
        with open("cluster_config.json", "w") as json_file:
            json.dump(roles_with_ips, json_file, indent=4)
        print("Generated 'cluster_config.json'.")
