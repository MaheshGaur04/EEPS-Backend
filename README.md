# Earth Energy Backend (Django + DRF + PostgreSQL)

## Run

```bash
cd Backend
venv\Scripts\activate
python manage.py migrate
python manage.py runserver 5000
```

API: http://localhost:5000/api/health

Create an administrator interactively when needed:

```bash
python manage.py createsuperuser
```

Configure secrets in `.env` (`USE_SQLITE=False` for PostgreSQL). Never use
development credentials or commit `.env` files in a production deployment.

## Deploy backend to Render

1. Push the project to GitHub and create a Render PostgreSQL database. Use the
   database's **internal** URL for the web service.
2. Create a Render **Web Service** for the repository with **Root Directory**
   `Backend`, runtime **Python**, build command:

   ```bash
   pip install -r requirements.txt && python manage.py collectstatic --noinput
   ```

   Start command:

   ```bash
   gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
   ```

   Health check path: `/api/health`.
3. Add these environment variables to the service:

   | Name | Value |
   | --- | --- |
   | `DEBUG` | `False` |
   | `SECRET_KEY` | A unique, long random secret |
   | `ALLOWED_HOSTS` | The Render hostname, without scheme (e.g. `earth-energy-api.onrender.com`) |
   | `DATABASE_URL` | Render PostgreSQL **internal** database URL |
   | `FRONTEND_URL` | Vercel production origin (e.g. `https://earth-energy.vercel.app`) |
   | `ACCESS_TOKEN_SECRET` | A unique, long random secret |
   | `REFRESH_TOKEN_SECRET` | A different unique, long random secret |
   | `REFRESH_COOKIE_SAMESITE` | `None` for separate `vercel.app` and `onrender.com` domains; see cookie note below |

   Generate each secret independently, for example on your local machine with
   `python -c "import secrets; print(secrets.token_urlsafe(50))"`, and paste the
   three different results into Render. Keep them private and do not commit them.

   Do not set `USE_SQLITE=True` in production. For Vercel preview origins, set
   `CORS_ALLOWED_ORIGINS` to an explicit comma-separated list of origins, each
   including `https://` and no trailing slash. Avoid wildcard origins because
   the API uses credentialed requests.
4. After the first deploy, run `python manage.py migrate --noinput` in the
   Render shell (or use Render's pre-deploy command if available). Create the
   first administrator with `python manage.py createsuperuser` in the shell.
   Do not use a shared/default admin password or the `seed_admin` command for
   deployment.
5. Verify `https://<render-hostname>/api/health` returns a successful JSON
   response.

The application refuses to start in production if strong, distinct secrets,
`ALLOWED_HOSTS`, an HTTPS `FRONTEND_URL`, or a PostgreSQL configuration are
missing. Set `DEBUG=False` explicitly in Render.

### Refresh-cookie setup

The API's refresh token is stored in an HTTP-only cookie. For the default
`*.vercel.app` frontend and `*.onrender.com` API, set
`REFRESH_COOKIE_SAMESITE=None`; production mode sets the cookie's `Secure` flag.
Browsers may block third-party cookies regardless, so for reliable refreshes,
use custom frontend and API hostnames on the same site (for example
`app.example.com` and `api.example.com`) and set `REFRESH_COOKIE_SAMESITE=Strict`.
Set `FRONTEND_URL` to the exact frontend origin. Configure the same origin in
`CORS_ALLOWED_ORIGINS` only if it differs from `FRONTEND_URL`.
