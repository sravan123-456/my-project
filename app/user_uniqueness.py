from app.models import User


def phone_exists_in_organization(phone, org_id):
    if not phone or not org_id:
        return False
    return (
        User.query.filter_by(organization_id=org_id, phone=phone).first() is not None
    )
