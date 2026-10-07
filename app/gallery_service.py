from datetime import date

from app.models import GalleryImage
from app.org_scope import org_query
from app.plan_enforcement import (
    count_gallery_items_for_year,
    gallery_photo_limit,
)


def get_gallery_years(org_id, festival_year=None):
    years = {
        row[0]
        for row in org_query(GalleryImage)
        .with_entities(GalleryImage.festival_year)
        .distinct()
        .all()
        if row[0]
    }
    if festival_year:
        years.add(int(festival_year))
    years.add(date.today().year)
    return sorted(years, reverse=True)


def count_gallery_photos(org_id, year):
    return (
        org_query(GalleryImage)
        .filter(GalleryImage.festival_year == year)
        .count()
    )


def max_gallery_photos_for_org(org):
    if not org:
        return 0
    cap = gallery_photo_limit(org)
    if cap is None:
        return None
    return cap


def gallery_has_room(org, year, extra=1):
    if not org:
        return False
    cap = gallery_photo_limit(org)
    if cap is None:
        return True
    return count_gallery_items_for_year(org, year) + extra <= cap


def resolve_gallery_year(org_id, year_arg, festival_year=None):
    available = get_gallery_years(org_id, festival_year)
    if year_arg and year_arg in available:
        return year_arg
    if festival_year and festival_year in available:
        return int(festival_year)
    return available[0] if available else date.today().year
