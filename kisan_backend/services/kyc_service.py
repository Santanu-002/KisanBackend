import uuid
from datetime import datetime
from fastapi import UploadFile
from kisan_backend.models.kyc import KYCDetails, KYCStatus
from kisan_backend.repositories.kyc_repository import KYCRepository
from kisan_backend.services.storage_service import storage_service
from loguru import logger

class KYCService:
    def __init__(self, kyc_repo: KYCRepository):
        self.kyc_repo = kyc_repo

    async def submit_kyc(
        self,
        user_id: uuid.UUID,
        document_type: str,
        address_line1: str,
        city: str,
        state: str,
        pincode: str,
        latitude: float,
        longitude: float,
        front_image: UploadFile,
        back_image: UploadFile,
        id_number: str = None,
        address_line2: str = None,
    ) -> KYCDetails:
        """
        Coordinates the KYC submission:
        1. Uploads images to R2.
        2. Saves metadata to DB.
        3. Updates user's kyc_completed status.
        """
        try:
            timestamp = int(datetime.utcnow().timestamp())
            
            # 1. Upload Images
            front_url = await storage_service.upload_file(
                front_image, 
                folder=f"kyc/{user_id}", 
                filename=f"front_{timestamp}.jpg"
            )
            back_url = await storage_service.upload_file(
                back_image, 
                folder=f"kyc/{user_id}", 
                filename=f"back_{timestamp}.jpg"
            )

            # 2. Check if KYC already exists for this user
            existing_kyc = await self.kyc_repo.get_by_user_id(user_id)
            if existing_kyc:
                # Update existing (simplification: we'll just overwrite or create new)
                # For this implementation, we overwrite fields
                kyc_record = existing_kyc
                kyc_record.document_type = document_type
                kyc_record.id_number = id_number
                kyc_record.front_image_url = front_url
                kyc_record.back_image_url = back_url
                kyc_record.latitude = latitude
                kyc_record.longitude = longitude
                kyc_record.address_line1 = address_line1
                kyc_record.address_line2 = address_line2
                kyc_record.city = city
                kyc_record.state = state
                kyc_record.pincode = pincode
                kyc_record.status = KYCStatus.PENDING # Reset to pending
                kyc_record.updated_at = datetime.utcnow()
            else:
                # Create new record
                kyc_record = KYCDetails(
                    user_id=user_id,
                    document_type=document_type,
                    id_number=id_number,
                    front_image_url=front_url,
                    back_image_url=back_url,
                    latitude=latitude,
                    longitude=longitude,
                    address_line1=address_line1,
                    address_line2=address_line2,
                    city=city,
                    state=state,
                    pincode=pincode,
                )
                await self.kyc_repo.create(kyc_record)

            # 3. Update User Status
            await self.kyc_repo.update_user_kyc_status(user_id, is_completed=True)
            
            # Commit the whole transaction (handled by session management usually)
            return kyc_record
            
        except Exception as e:
            logger.error(f"KYC Submission failed for user {user_id}: {str(e)}")
            raise e
