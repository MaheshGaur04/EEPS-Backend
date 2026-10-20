# Earth Energy Backend (Django + DRF + PostgreSQL)

## Run

```bash
cd Backend
venv\Scripts\activate
python manage.py migrate
python manage.py seed_admin --password "use-a-strong-unique-password"
python manage.py runserver 5000
```

API: http://localhost:5000/api/health

For a Render web service, install from `requirements.txt` and start the app with:

```bash
python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

The seed command creates `admin@earthenergy.local` unless `--email` is supplied.
It requires an explicit password and does not install a default admin credential.
API registration requires a password of at least 12 characters and applies the
configured Django password validators.

Configure local settings in `.env` (`USE_SQLITE=False` for PostgreSQL). For local
development, `DEBUG=True` is expected. Do not use the example secret values in
`.env.example` outside local development.

## Production configuration

Set `DEBUG=False`, provide explicit `ALLOWED_HOSTS`, and set three different
random secrets of at least 32 characters for `SECRET_KEY`,
`ACCESS_TOKEN_SECRET`, and `REFRESH_TOKEN_SECRET`. Generate each value separately
with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Production startup fails if these secrets are missing, too short, placeholder
values, or reused. Session, CSRF, and refresh-token cookies are marked secure
when `DEBUG=False`.

PostgreSQL connections are reused for up to 60 seconds by default. Set
`DB_CONN_MAX_AGE=0` to disable reuse, or choose a duration appropriate for the
database connection limit and the total number of application workers and
instances. Connection health checks run before a reused connection is used.

### Shared cache and API throttling

Production requires a shared Redis cache so API throttling works consistently
across Render instances. Create or use a private Render Key Value service and add
`REDIS_URL` to the backend web service using the Key Value service's **internal
connection URL**. Keep the Redis service private; do not expose its URL in source
control or frontend environment variables. Local development uses an in-process
cache when `REDIS_URL` is unset.

Set `NUM_PROXIES=1` for Render's single trusted reverse-proxy hop. If the
deployment proxy topology changes, set this to the actual number of trusted
proxies in front of Django. This controls which forwarded client IP is used as
the throttle key. Use a distinct `CACHE_KEY_PREFIX` if production and staging
share a Redis service; otherwise they can affect each other's throttles.
ROI calculations are limited to two requests per authenticated account in a
rolling 24-hour window; the limit is enforced through this shared cache.

Configure HTTPS redirect and HSTS to match the hosting provider. Set
`SECURE_SSL_REDIRECT=True` only after verifying that Django correctly recognizes
HTTPS behind any reverse proxy; misconfiguration can cause redirect loops.
Enable HSTS only after confirming HTTPS works for the entire domain, and increase
`SECURE_HSTS_SECONDS` cautiously.
