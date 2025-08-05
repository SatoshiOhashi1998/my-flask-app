from app import create_app

def test_app_creation():
    app = create_app()
    assert app is not None
    assert app.permanent_session_lifetime.total_seconds() == 300
    assert 'main' in app.blueprints

def test_cors_headers():
    app = create_app()
    client = app.test_client()
    res = client.get('/')
    assert 'Access-Control-Allow-Origin' in res.headers

