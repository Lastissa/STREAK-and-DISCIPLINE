"""THIS FILE HANDLES ANY THING THAT HAVE TO DO WITH UPLOADING FILES BUT FOR NOW FOCUS IS ON IMAGES ONLY"""

import cloudinary.uploader
from django.conf import settings


cloudinary.config(
    cloud_name = settings.CLOUDINARY_CLOUD_NAME,
    api_key = settings.CLOUDINARY_API_KEY,
    api_secret = settings.CLOUDINARY_API_SECRET
)

def upload_profile_picture(uploaded_file: bytes, user_email:str, old_user_email=None) -> dict:
    """
    Upload and compress a profile picture to Cloudinary.
    
    Args:
        uploaded_file: File from request.FILES['avatar'] 
        user_email: User's ID for folder organization ---- EMails(upprt)
        old_public_id: Previous avatar public_id to delete -DEFAULT TO NONR
    
    Returns:
        dict with 'url' and 'public_id' keys
    """
    # Delete old avatar if exists
    if old_user_email:
        try:    cloudinary.uploader.destroy(old_user_email)
        except Exception:   pass  # Old image might already be gone
    
    # Upload with aggressive compression
    result = cloudinary.uploader.upload(
        uploaded_file,
        folder=f"discipline_and_streak_profile_picture/{user_email}/",
        public_id=f"profile_{user_email}",
        overwrite=True,
        eager=[{
            'width': 200,
            'height': 200,
            'crop': 'fill',
            'gravity': 'face',
            'quality': 40,          # Low quality - it's just a tiny profile pic
            'fetch_format': 'auto',  # WebP for modern browsers
        }],
        eager_async=True,           # Process in background
        resource_type='image',
        allowed_formats=['jpg', 'jpeg', 'png', 'webp'],
        max_file_size=3 * 1024 * 1024,  # 3MB max before upload, it it not reach sef
    )
    
    return {
        'url': result['eager'][0]['secure_url'],  # Use eager transformed version
        'public_id': result['public_id']
    }


def delete_profile_picture(user_email):
    """Delete an profile picture from Cloudinary.where public id is thier email in upper"""
    if user_email:
        try:
            cloudinary.uploader.destroy(user_email)
            return True
        except Exception:
            return False
    return False




def upload_news_banner(uploaded_file: bytes, id: int)-> dict:
    """name tag is the id of that news, save the news first and them grab the  id collect image link, save the link also"""
    result = cloudinary.uploader.upload(
        uploaded_file,
        folder=f"discipline_and_streak_profile_picture/NEWS/BANNERS/",
        public_id=f"news_banner_{id}",
        overwrite=True,
        eager=[{
            'width': 200,
            'height': 200,
            'crop': 'fill',
            'gravity': 'face',
            'quality': 100,          # okay quality - it's just a  banner
            'fetch_format': 'auto',
        }],
        eager_async=True,           # Process in background
        resource_type='image',
        allowed_formats=['jpg', 'jpeg', 'png', 'webp'],
        max_file_size=3 * 1024 * 1024,  # 3MB max before upload
    )
    return {
        'url': result['eager'][0]['secure_url'],  # Use eager transformed version
        'public_id': result['public_id']
        }