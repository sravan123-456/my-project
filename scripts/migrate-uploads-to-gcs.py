#!/usr/bin/env python3
"""Copy existing local profile/gallery images to GCS when GCS_BUCKET_NAME is set."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import GalleryImage, User
from app.storage import upload_local_file, uses_gcs, _local_path


def main():
    app = create_app()
    with app.app_context():
        if not uses_gcs():
            print("GCS_BUCKET_NAME is not set. Nothing to migrate.")
            return 1

        migrated = 0
        skipped = 0

        for user in User.query.filter(User.profile_photo_key.isnot(None)).all():
            key = user.profile_photo_key
            local = _local_path(key)
            if os.path.isfile(local):
                if upload_local_file(local, key):
                    migrated += 1
                    print(f"profile: {key}")
                else:
                    skipped += 1
            else:
                skipped += 1

        for image in GalleryImage.query.all():
            key = image.storage_key
            local = _local_path(key)
            if os.path.isfile(local):
                if upload_local_file(local, key):
                    migrated += 1
                    print(f"gallery: {key}")
                else:
                    skipped += 1
            else:
                skipped += 1

        print(f"Done. migrated={migrated} skipped={skipped}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
