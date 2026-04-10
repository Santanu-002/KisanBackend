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

    async def upload_file(self, file: UploadFile, folder: str, filename: str) -> str:
        """
        Uploads a file to S3/R2 and returns the public URL.
        """
        path = f"{folder}/{filename}"
        
        try:
            async with self.session.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(
                    signature_version="s3v4",
                    s3={'addressing_style': 'path'}
                ),
            ) as s3:
                # Read file content
                content = await file.read()
                
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=path,
                    Body=content,
                    ContentType=file.content_type or "application/octet-stream",
                )
                
                logger.info(f"File uploaded successfully to: {path}")
                
                # Construct public URL
                if self.public_url_prefix:
                    return f"{self.public_url_prefix.rstrip('/')}/{path}"
                
                # Fallback to endpoint-based URL
                return f"{self.endpoint_url}/{self.bucket_name}/{path}"
                
        except Exception as e:
            logger.error(f"Error uploading file to storage: {str(e)}")
            raise e
        finally:
            await file.seek(0) # Reset file pointer for potential re-reads

storage_service = StorageService()
