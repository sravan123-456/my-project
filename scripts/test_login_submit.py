import re

from app import create_app
from app.models import Organization, User

app = create_app()

with app.test_client() as client:
    response = client.get("/login")
    html = response.data.decode()
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    csrf = match.group(1) if match else ""

    response = client.post(
        "/login",
        data={
            "csrf_token": csrf,
            "committee_code": "indukuru",
            "username": "testuser",
            "password": "wrong",
            "login_submit": "Login",
            "active_tab": "existing",
        },
        follow_redirects=True,
    )
    body = response.data.decode()
    handled = "Invalid committee code" in body or "Invalid committee code, username, or password" in body
    print("login_submit_handled:", handled)
    print("status:", response.status_code)

with app.app_context():
    org = Organization.query.first()
    user = User.query.filter_by(is_approved=True).first()
    if org and user:
        print("sample_org:", org.slug)
        print("sample_user:", user.username)
