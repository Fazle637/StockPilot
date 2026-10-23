from app import create_app

app = create_app()

if __name__ == "__main__":
    print(
        "Real SECRET_KEY loaded:",
        app.config["SECRET_KEY"] != "dev-only-change-me"
    )
    print("Session cookie name:", app.config["SESSION_COOKIE_NAME"])
    app.run(debug=True)