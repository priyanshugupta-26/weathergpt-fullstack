"""
Comprehensive automated tests for WeatherGPT Strict Authentication Gate and Route Protection.
Validates:
1. Unauthenticated root route redirects to /register (302)
2. Direct protected URLs (/dashboard, /globe, /forecast, /model-lab, /data-lab, /admin, /setup)
   redirect or deny unauthenticated access on the server side
3. Registration success with automatic session creation
4. Duplicate email rejection (409)
5. Short password and mismatched password rejection (400)
6. Passwords stored securely hashed (Argon2), never plaintext
7. Login success with email or mobile
8. Login failure on invalid credentials (401)
9. Logout clearing session cookie and revoking session
10. Protected APIs return 401 for unauthenticated requests
11. Authenticated user access to portal pages
12. Normal user cannot access admin (/api/admin -> 403, /admin -> 403)
13. Normal user cannot access setup credentials (/api/setup -> 403, /setup -> 403)
14. Admin access works for admin users
15. Preferred language and profile details stored and persisted
"""
import pytest
from backend.database import Session, User, AuthSession
from backend.auth import hasher
from sqlalchemy import select


def test_unauthenticated_root_redirects_to_login_or_register(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] in ("/login", "/register")


@pytest.mark.parametrize(
    "path",
    [
        "/dashboard",
        "/globe",
        "/forecast",
        "/chat",
        "/alerts",
        "/climate",
        "/agriculture",
        "/aviation",
        "/marine",
        "/city-monitor",
        "/model-lab",
        "/data-lab",
        "/settings",
        "/profile",
    ],
)
def test_direct_portal_routes_redirect_unauthenticated(client, path):
    r = client.get(path, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] in ("/login", "/register")


def test_admin_and_setup_redirect_or_deny_unauthenticated(client):
    r_admin = client.get("/admin", follow_redirects=False)
    assert r_admin.status_code == 302
    assert r_admin.headers["location"] in ("/register", "/login")

    r_setup = client.get("/setup", follow_redirects=False)
    assert r_setup.status_code in (302, 403)
    if r_setup.status_code == 302:
        assert r_setup.headers["location"] in ("/login", "/register")


def test_registration_success_and_automatic_login(client):
    payload = {
        "email": "priya.sharma@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "full_name": "Priya Sharma",
        "mobile": "+91 98765 43210",
        "state": "Bihar",
        "district": "Patna",
        "preferred_language": "hi",
    }
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "priya.sharma@example.com"
    assert data["name"] == "Priya Sharma"
    assert data["preferred_language"] == "hi"
    assert "password" not in data
    assert "password_hash" not in data

    # Verify automatic login via session cookie
    assert "wg_session" in client.cookies

    # Verify password was stored hashed with Argon2 in DB
    with Session() as db:
        user = db.scalar(select(User).where(User.email == "priya.sharma@example.com"))
        assert user is not None
        assert user.password_hash != "Password123!"
        assert hasher.verify(user.password_hash, "Password123!")
        assert user.preferred_language == "hi"
        assert user.mobile == "9876543210"

    # Authenticated user can now view /dashboard (FileResponse 200)
    dash = client.get("/dashboard", follow_redirects=False)
    assert dash.status_code == 200


def test_duplicate_email_rejected(client):
    payload = {
        "email": "duplicate.user@example.com",
        "password": "ValidPassword123!",
        "confirm_password": "ValidPassword123!",
        "full_name": "User One",
    }
    r1 = client.post("/api/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/api/auth/register", json=payload)
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"].lower()


def test_invalid_password_rejected(client):
    # Passwords do not match
    r_mismatch = client.post(
        "/api/auth/register",
        json={
            "email": "mismatch@example.com",
            "password": "Password123!",
            "confirm_password": "DifferentPassword!",
            "full_name": "Mismatch User",
        },
    )
    assert r_mismatch.status_code == 400
    assert "match" in r_mismatch.json()["detail"].lower()

    # Password too short
    r_short = client.post(
        "/api/auth/register",
        json={
            "email": "short@example.com",
            "password": "short",
            "confirm_password": "short",
            "full_name": "Short User",
        },
    )
    assert r_short.status_code in (400, 422)


def test_login_success_and_wrong_password_failure(client):
    client.cookies.clear()
    reg_payload = {
        "email": "login.test@example.com",
        "password": "CorrectPassword123!",
        "confirm_password": "CorrectPassword123!",
        "full_name": "Login Tester",
        "mobile": "9811122233",
        "preferred_language": "te",
    }
    r = client.post("/api/auth/register", json=reg_payload)
    assert r.status_code == 201

    # Clear cookie to test fresh login
    client.cookies.clear()

    # Wrong password fails with 401
    r_bad = client.post(
        "/api/auth/login",
        json={"email": "login.test@example.com", "password": "WrongPassword!"},
    )
    assert r_bad.status_code == 401
    assert "invalid" in r_bad.json()["detail"].lower()

    # Login with email succeeds
    r_good = client.post(
        "/api/auth/login",
        json={"email": "login.test@example.com", "password": "CorrectPassword123!"},
    )
    assert r_good.status_code == 200
    assert r_good.json()["preferred_language"] == "te"
    assert "wg_session" in client.cookies

    # Login with mobile number also succeeds
    client.cookies.clear()
    r_mobile = client.post(
        "/api/auth/login",
        json={"mobile": "9811122233", "password": "CorrectPassword123!"},
    )
    assert r_mobile.status_code == 200
    assert r_mobile.json()["email"] == "login.test@example.com"


def test_logout(client):
    client.post(
        "/api/auth/login",
        json={"email": "login.test@example.com", "password": "CorrectPassword123!"},
    )
    assert "wg_session" in client.cookies

    r_out = client.post("/api/auth/logout")
    assert r_out.status_code == 200

    # Cookie cleared and subsequent protected requests fail with redirect or 401
    r_dash = client.get("/dashboard", follow_redirects=False)
    assert r_dash.status_code == 302
    assert r_dash.headers["location"] in ("/login", "/register")


def test_protected_api_returns_401(client):
    client.cookies.clear()
    # Saved locations requires auth
    r_loc = client.get("/api/locations/saved")
    assert r_loc.status_code == 401

    # Profile requires auth
    r_prof = client.get("/api/profile")
    assert r_prof.status_code == 401

    # Chat history requires auth
    r_chat = client.get("/api/chat/history")
    assert r_chat.status_code == 401


def test_normal_user_cannot_access_admin_or_setup(client):
    # Log in as normal user
    client.post(
        "/api/auth/login",
        json={"email": "login.test@example.com", "password": "CorrectPassword123!"},
    )
    # Admin API returns 403 Forbidden
    r_admin_api = client.get("/api/admin")
    assert r_admin_api.status_code == 403

    # Admin UI route returns 403 Forbidden
    r_admin_ui = client.get("/admin", follow_redirects=False)
    assert r_admin_ui.status_code == 403

    # Setup UI route returns 403 Forbidden
    r_setup_ui = client.get("/setup", follow_redirects=False)
    assert r_setup_ui.status_code == 403

    # Setup API post returns 403 Forbidden
    r_setup_post = client.post("/api/setup", json={"ai_provider": "auto"})
    assert r_setup_post.status_code == 403


def test_admin_access_works(client):
    # Create an admin user in the database
    with Session.begin() as db:
        admin_user = User(
            email="superadmin@weathergpt.gov.in",
            name="Super Admin",
            password_hash=hasher.hash("AdminPass123!"),
            role="admin",
            preferred_language="en",
        )
        db.add(admin_user)

    client.cookies.clear()
    login_r = client.post(
        "/api/auth/login",
        json={"email": "superadmin@weathergpt.gov.in", "password": "AdminPass123!"},
    )
    assert login_r.status_code == 200
    assert login_r.json()["role"] == "admin"

    # Admin UI route works (FileResponse 200)
    r_admin_ui = client.get("/admin", follow_redirects=False)
    assert r_admin_ui.status_code == 200

    # Admin API works
    r_admin_api = client.get("/api/admin")
    assert r_admin_api.status_code == 200
    assert "users" in r_admin_api.json()


def test_preferred_language_saved_and_persisted(client):
    # Login as user
    client.post(
        "/api/auth/login",
        json={"email": "login.test@example.com", "password": "CorrectPassword123!"},
    )

    # Update language to Tamil ('ta')
    r_patch = client.patch(
        "/api/profile",
        json={"name": "Login Tester", "language": "ta", "preferred_language": "ta"},
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["preferred_language"] == "ta"

    # Retrieve profile to verify persistence
    r_prof = client.get("/api/profile")
    assert r_prof.status_code == 200
    assert r_prof.json()["preferred_language"] == "ta"


@pytest.mark.parametrize("path", ["/register", "/login"])
def test_unauthenticated_can_access_auth_pages(client, path):
    client.cookies.clear()
    r = client.get(path, follow_redirects=False)
    assert r.status_code == 200


def test_onboarding_access_control(client):
    client.cookies.clear()
    # Unauthenticated user is redirected to /register
    r_unauth = client.get("/onboarding", follow_redirects=False)
    assert r_unauth.status_code == 302
    assert r_unauth.headers["location"] in ("/login", "/register")

    # Authenticated user can access onboarding
    client.post(
        "/api/auth/login",
        json={"email": "login.test@example.com", "password": "CorrectPassword123!"},
    )
    r_auth = client.get("/onboarding", follow_redirects=False)
    assert r_auth.status_code == 200


def test_profile_language_persistence_multiple_languages(client):
    client.post(
        "/api/auth/login",
        json={"email": "login.test@example.com", "password": "CorrectPassword123!"},
    )
    for lang in ["hi", "te", "ur", "bn", "gu", "kn", "ml", "mr", "pa", "ta"]:
        r = client.patch("/api/profile", json={"preferred_language": lang})
        assert r.status_code == 200
        assert r.json()["preferred_language"] == lang


