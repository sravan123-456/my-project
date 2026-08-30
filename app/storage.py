import os
import uuid
from io import BytesIO

from flask import current_app, send_file
from werkzeug.utils import secure_filename

IMAGE_EXTENSIONS = frozenset({"png", "jpg", "jpeg", "gif", "webp"})
CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}

_gcs_client = None


def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in IMAGE_EXTENSIONS


def _extension(filename):
    return secure_filename(filename).rsplit(".", 1)[1].lower()


def _content_type(ext):
    return CONTENT_TYPES.get(ext, "application/octet-stream")


def uses_gcs():
    return bool(current_app.config.get("GCS_BUCKET_NAME"))


def _get_gcs_bucket():
    global _gcs_client
    from google.cloud import storage

    if _gcs_client is None:
        _gcs_client = storage.Client()
    return _gcs_client.bucket(current_app.config["GCS_BUCKET_NAME"])


def _local_path(storage_key):
    return os.path.join(current_app.config["UPLOAD_FOLDER"], storage_key)


def save_image(file, prefix):
    if not file or file.filename == "":
        return None
    if not allowed_image(file.filename):
        return None

    ext = _extension(file.filename)
    storage_key = f"{prefix}/{uuid.uuid4().hex}.{ext}"
    content_type = _content_type(ext)

    if uses_gcs():
        bucket = _get_gcs_bucket()
        blob = bucket.blob(storage_key)
        file.seek(0)
        blob.upload_from_file(file, content_type=content_type)
    else:
        full_path = _local_path(storage_key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        file.seek(0)
        file.save(full_path)

    return storage_key


def delete_image(storage_key):
    if not storage_key:
        return

    if uses_gcs():
        bucket = _get_gcs_bucket()
        blob = bucket.blob(storage_key)
        if blob.exists():
            blob.delete()
    else:
        path = _local_path(storage_key)
        if os.path.isfile(path):
            os.remove(path)


def make_image_response(storage_key):
    if uses_gcs():
        bucket = _get_gcs_bucket()
        blob = bucket.blob(storage_key)
        if not blob.exists():
            return None
        data = blob.download_as_bytes()
        ext = storage_key.rsplit(".", 1)[-1].lower()
        return send_file(BytesIO(data), mimetype=_content_type(ext))

    path = _local_path(storage_key)
    if not os.path.isfile(path):
        return None
    ext = storage_key.rsplit(".", 1)[-1].lower()
    return send_file(path, mimetype=_content_type(ext))
