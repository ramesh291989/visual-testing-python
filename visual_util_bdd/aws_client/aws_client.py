import boto3
import botocore
import os


class Singleton(type):
    ''' Singleton always return same session '''
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(
                Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class AWSSession(metaclass=Singleton):

    def __init__(self):
        self.session = None
        self.get_aws_session()

    def get_aws_session(self):
        ''' return AWS session '''
        if not self.session:
            if os.environ.get('CROSS_ACCOUNT_ROLE'):
                sts = boto3.client('sts')
                response = sts.assume_role(
                    RoleArn=os.environ['CROSS_ACCOUNT_ROLE'],
                    RoleSessionName='Applihealth-RoleSession'
                )
                creds = response['Credentials']
                self.session = boto3.Session(
                    aws_access_key_id=creds['AccessKeyId'],
                    aws_secret_access_key=creds['SecretAccessKey'],
                    aws_session_token=creds['SessionToken'])
            elif os.environ.get('AWS_PROFILE'):
                self.session = boto3.Session(
                    profile_name=os.environ.get('AWS_PROFILE'))
            else:
                self.session = boto3.session.Session()
        return self.session


class AWSMapper():
    def __init__(self):
        self.session = None
        aws_obj = AWSSession()
        self.session = aws_obj.session

    def client(self, service):
        ''' return aws client for specific services '''
        if(self.session):
            return self.session.client(service)
        return boto3.client(service)

    def resource(self, service):
        ''' return aws resource for specific services '''
        if(self.session):
            return self.session.resource(service)
        return boto3.resource(service)
