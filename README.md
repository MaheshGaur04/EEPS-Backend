# Earth Energy Backend (Django + DRF + PostgreSQL)

## Run

```bash
cd Backend
venv\Scripts\activate
python manage.py migrate
python manage.py seed_admin
python manage.py runserver 5000
```

API: http://localhost:5000/api/health

Default admin: `admin@earthenergy.local` / `Admin@12345`

Configure secrets in `.env` (`USE_SQLITE=False` for PostgreSQL).
