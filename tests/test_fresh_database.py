from app import create_app, db


def test_fresh_database_works_without_manual_setup(tmp_path):
    db_file = tmp_path / "fresh.db"

    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + db_file.as_posix(),
        "WTF_CSRF_ENABLED": False,
    })

    response = app.test_client().post(
        "/register",
        data={
            "username": "fresh_user",
            "email": "fresh_user@example.com",
            "password": "TestPassword123!",
        },
    )

    with app.app_context():
        db.session.remove()
        db.engine.dispose()

    assert response.status_code == 302
