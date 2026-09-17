import asyncio
import cloudinary
import cloudinary.uploader

from .config import cloudinary_config

cloudinary.config(**cloudinary_config, secure=True)

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # Discord embed images are fetched by Discord itself, not proxied through us, so this just keeps Cloudinary storage/bandwidth sane.

class UploadError(Exception):
    """Raised for any rejected upload; the message is safe to show the user."""

async def upload_embed_image(file_storage, guild_id: int) -> str:
    """Validate and upload an embed image/icon to Cloudinary. Returns the secure URL."""
    if file_storage is None or not file_storage.filename:
        raise UploadError("No file provided.")

    if file_storage.content_type not in ALLOWED_CONTENT_TYPES:
        raise UploadError("Only PNG, JPEG, GIF, and WEBP images are allowed.")

    data = file_storage.read()
    if not data:
        raise UploadError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadError("Images must be 8MB or smaller.")

    # to_thread: cloudinary.uploader.upload() is a blocking network call.
    result = await asyncio.to_thread(
        cloudinary.uploader.upload,
        data,
        folder=f"{guild_id}",
        resource_type="image",
    )
    return result["secure_url"]

async def upload_rank_card_image(file_storage) -> str:
    """Validate and upload a rank card background to Cloudinary. Returns the secure URL."""
    if file_storage is None or not file_storage.filename:
        raise UploadError("No file provided.")

    if file_storage.content_type not in ALLOWED_CONTENT_TYPES:
        raise UploadError("Only PNG, JPEG, GIF, and WEBP images are allowed.")

    data = file_storage.read()
    if not data:
        raise UploadError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadError("Images must be 8MB or smaller.")

    result = await asyncio.to_thread(
        cloudinary.uploader.upload,
        data,
        folder="_level-cards",
        resource_type="image",
    )
    return result["secure_url"]
