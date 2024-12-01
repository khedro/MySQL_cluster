import boto3
import json

# AWS Configuration
REGION = "us-east-1"  # Replace with your AWS region

# Instance roles to map
roles = {
    "Manager": None,
    "Proxy": None,
    "Worker1": None,
    "Worker2": None,
    "GateKeeper": None,
    "TrustedHost": None
}

# Initialize Boto3 EC2 client
ec2 = boto3.client('ec2', region_name=REGION)


def fetch_instance_ips():
    """
    Fetches the private IPs of currently running instances and updates the roles dictionary.
    """
    # Fetch all running instances
    response = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            name_tag = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), None)
            if name_tag in roles:
                roles[name_tag] = instance['PrivateIpAddress']

    return roles


def save_to_json(filename="cluster_config.json"):
    """
    Saves the current state of roles with their IPs to a JSON file.
    """
    with open(filename, "w") as json_file:
        json.dump(roles, json_file, indent=4)
    print(f"Generated '{filename}'.")


# Main execution
if __name__ == "__main__":
    roles_with_ips = fetch_instance_ips()

    # Separate missing roles for clearer debugging
    missing_roles = [role for role, ip in roles_with_ips.items() if ip is None]

    if missing_roles:
        print(f"The following roles are missing IPs: {missing_roles}")
        print("Partial JSON will be generated. Run the script again after all instances are up.")
    else:
        print("All roles are mapped successfully.")

    # Generate JSON file (partial or complete)
    save_to_json()
