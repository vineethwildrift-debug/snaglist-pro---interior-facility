from snaglist_pro.web.app import app


def test_login_page_available():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Snaglist Pro" in response.data
    assert b"Developed by Vineeth.Bisa" in response.data


def test_admin_login_redirects_to_dashboard():
    client = app.test_client()
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_dashboard_requires_login():
    client = app.test_client()
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/" in response.headers["Location"]
