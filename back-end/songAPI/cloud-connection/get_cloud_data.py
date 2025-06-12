# Goal: Write a script to input a file name and receive a file URL as output
import os
import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()
endpoint_url = os.getenv('B2_ENDPOINT')
aws_access_key_id = os.getenv('B2_APPLICATION_ID')
aws_secret_access_key = os.getenv('B2_APPLICATION_KEY')

print(f'{endpoint_url}')
print(f'{aws_access_key_id}')
print(f'{aws_secret_access_key}')

b2 = boto3.resource(
  service_name='s3',
  endpoint_url=endpoint_url,
  aws_access_key_id=aws_access_key_id,
  aws_secret_access_key=aws_secret_access_key,
  config=Config(signature_version='s3v4')
)

print('b2: ', b2)

bucket = b2.Bucket('brasileiro')
print('bucket: ', bucket)

url = b2.meta.client.generate_presigned_url(
    ClientMethod='get_object',
    Params={
      'Bucket': bucket.name,
      'Key': 'wave.pdf'
    }
  )

print(url)



# b2.Bucket(bucket_name)

# b2.meta.client.generate_presigned_url(ClientMethod='get_object', ExpiresIn=3000,Params={'Bucket': bucket.name, 'Key': song.key})

# # For console use
# b2 = boto3.resource(service_name='s3',
#   endpoint_url=B2_ENDPOINT,
#   aws_access_key_id=B2_APPLICATION_ID,
#   aws_secret_access_key=B2_APPLICATION_KEY,
#   config=Config(signature_version='s3v4')
#   )