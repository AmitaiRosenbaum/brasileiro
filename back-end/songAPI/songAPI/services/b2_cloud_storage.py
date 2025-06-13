from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

class SheetMusicStorage(S3Boto3Storage):
  file_overwrite = False