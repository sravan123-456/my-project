from datetime import date

from app.models import GalleryImage
from app.org_scope import org_query

GALLERY_MAX_PHOTOS_PER_YEAR = 20


def get_gallery_years(org_id):
    years = {
        row[0]
        for row in org_query(GalleryImage)
        .with_entities(GalleryImage.festival_year)
        .distinct()
        .all()
        if row[0]
    }
    years.add(date.today().year)
    return sorted(years, reverse=True)


def count_gallery_photos(org_id, year):
    return (
        org_query(GalleryImage)
        .filter(GalleryImage.festival_year == year)
        .count()
    )


def gallery_has_room(org_id, year, limit=GALLERY_MAX_PHOTOS_PER_YEAR):
    return count_gallery_photos(org_id, year) < limit


def resolve_gallery_year(org_id, year_arg):
    available = get_gallery_years(org_id)
    if year_arg and year_arg in available:
        return year_arg
    return available[0] if available else date.today().year
