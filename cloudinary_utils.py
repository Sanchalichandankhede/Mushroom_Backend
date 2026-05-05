import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

def upload_image(file_path: str, folder: str = "mushroom_detection") -> str:
    """
    Upload an image from a local file path to Cloudinary.
    Returns the secure URL of the uploaded image.
    """
    try:
        response = cloudinary.uploader.upload(
            file_path,
            folder=folder,
            resource_type="image"
        )
        return response.get("secure_url")
    except Exception as e:
        print(f"Cloudinary Upload Error: {e}")
        return ""

def upload_image_stream(file_stream, folder: str = "mushroom_detection") -> str:
    """
    Upload an image from a file stream (e.g., from FastAPI UploadFile) to Cloudinary.
    Returns the secure URL of the uploaded image.
    """
    try:
        response = cloudinary.uploader.upload(
            file_stream,
            folder=folder,
            resource_type="image"
        )
        return response.get("secure_url")
    except Exception as e:
        print(f"Cloudinary Upload Error: {e}")
        return ""
