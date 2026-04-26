from typing import List
import uuid
import aioboto3
from botocore.config import Config
from fastapi import UploadFile
from kisan_backend.core.config import settings
from loguru import logger

class StorageService:
    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.access_key = settings.S3_ACCESS_KEY_ID
        self.secret_key = settings.S3_SECRET_ACCESS_KEY
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.S3_REGION
        self.public_url_prefix = settings.S3_PUBLIC_URL_PREFIX

    async def get_presigned_url(self, file_key: str, content_type: str = "image/jpeg", expires_in: int = 3600) -> str:
        """
        Generates a presigned URL for uploading a file to S3/R2.
        """
        try:
            async with self.session.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(signature_version="s3v4"),
            ) as s3:
                return await s3.generate_presigned_url(
                    ClientMethod='put_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': file_key,
                        'ContentType': content_type,
                    },
                    ExpiresIn=expires_in
                )
        except Exception as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise e

    async def get_view_url(self, file_key: str, expires_in: int = 3600) -> str:
        """
        Generates a presigned URL for viewing a private file.
        Extracts the key if a full URL is provided.
        """
        if not file_key:
            return ""

        # If it's a full URL, extract the relative key
        if self.public_url_prefix and file_key.startswith(self.public_url_prefix):
            file_key = file_key.replace(self.public_url_prefix, "").lstrip("/")
        elif self.endpoint_url and file_key.startswith(self.endpoint_url):
            # Also handle if it's prefixed with the endpoint URL
            file_key = file_key.replace(self.endpoint_url, "").lstrip("/")
            # If the bucket name is also in there (path style)
            if file_key.startswith(self.bucket_name):
                file_key = file_key.replace(self.bucket_name, "", 1).lstrip("/")
        elif "://" in file_key:
            # Fallback: take everything after the host
            parts = file_key.split("/")
            if len(parts) > 3:
                file_key = "/".join(parts[3:])

        try:
            async with self.session.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(signature_version="s3v4"),
            ) as s3:
                return await s3.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': file_key,
                    },
                    ExpiresIn=expires_in
                )
        except Exception as e:
            logger.error(f"Error generating view URL: {str(e)}")
            return file_key  # Return original as fallback

    async def upload_file(self, file: UploadFile, folder: str, filename: str) -> str:
        """
        Uploads a file stream directly to S3/R2 and returns the public URL.
        Uses `aioboto3` for high-throughput async processing.
        """
        file_key = f"{folder}/{filename}"
        try:
            content = await file.read()
            async with self.session.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            ) as s3:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=file_key,
                    Body=content,
                    ContentType=file.content_type or "image/jpeg"
                )
                
            public_prefix = self.public_url_prefix or self.endpoint_url
            return f"{public_prefix}/{file_key}"
            
        except Exception as e:
            logger.error(f"Error uploading file to storage: {str(e)}")
            raise e
        finally:
            await file.seek(0)

    async def list_objects(self, prefix: str) -> List[str]:
        """
        Lists public URLs for objects within a given prefix.
        """
        try:
            async with self.session.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            ) as s3:
                response = await s3.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix
                )
                
                urls = []
                if 'Contents' in response:
                    public_prefix = self.public_url_prefix or self.endpoint_url
                    for obj in response['Contents']:
                        if obj['Key'] != prefix:
                            urls.append(f"{public_prefix}/{obj['Key']}")
                return urls
        except Exception as e:
            logger.error(f"Error listing objects: {str(e)}")
            raise e

storage_service = StorageService()
