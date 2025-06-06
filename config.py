import boto3


class AWSConfig:
    def __init__(self, region_name='ap-south-1'):
        self.region_name = region_name
        self.ssm_client = boto3.client('ssm', region_name=self.region_name)

    def get_parameter(self, name, with_decryption=True):
        return self.ssm_client.get_parameter(Name=name, WithDecryption=with_decryption)


