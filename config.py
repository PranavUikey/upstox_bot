import boto3


class AWSConfig:
    def __init__(self, region_name='ap-south-1'):
        self.region_name = region_name
        self.ssm_client = boto3.client('ssm', region_name=self.region_name)

    def get_parameter(self, name, with_decryption=True):
        return self.ssm_client.get_parameter(Name=name, WithDecryption=with_decryption)


# aws_config = AWSConfig()
# access_token = aws_config.get_parameter('/upstox/access_token')['Parameter']['Value']
# client_id = aws_config.get_parameter('/upstox/client_id')['Parameter']['Value']
# redirect_uri = aws_config.get_parameter('/upstox/redirect_uri')['Parameter']['Value']
# client_secret = aws_config.get_parameter('/upstox/client_secret')['Parameter']['Value']

# print(f"Access Token: {access_token}")
# print(f"Client ID: {client_id}")
# print(f"Redirect URI: {redirect_uri}")
# print(f"Client Secret: {client_secret}")