# Security Policy

## Implemented safeguards

- Passwords are stored as hashes using Werkzeug's scrypt password-hashing method.
- Authentication is handled using Flask-Login.
- Role-based permissions are enforced on the server.
- Database queries restrict access to resources according to ownership where applicable.
- Forms use CSRF protection.
- API endpoints require authentication where appropriate.
- Product image uploads have file type, file size, and image validation checks.
- User input is validated before database operations.

## Reporting a vulnerability

Please report security issues privately to the project maintainer.
Do not publish credentials, session cookies, personal data, or exploit details
that could expose other users.

## Deployment

- Never commit .env or production secrets.
- Replace demo credentials before deployment.
- Use HTTPS in production.
- Configure a strong, unique SECRET_KEY.
- Review database permissions and ownership checks before release.
