# Local development on Windows

Use Python 3.14 and Node.js 24. Run backend commands from this repository (`kavehmetal back\tg1`). These commands work in PowerShell without activating a virtual environment or changing execution policy.

## Install the backend

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate --settings=tg1.settings_local
.\.venv\Scripts\python.exe manage.py createsuperuser --settings=tg1.settings_local
.\start-local.cmd
```

Backend: http://127.0.0.1:8000/api/

Django admin: http://127.0.0.1:8000/django-admin/

If an administrator was provisioned during local setup, its username, email, and generated password are in the ignored `.env.local` file in this repository. Otherwise use `createsuperuser` above to choose your own credentials. To change a password, run `.\.venv\Scripts\python.exe manage.py changepassword admin --settings=tg1.settings_local`.

`tg1.settings_local` uses a fresh SQLite database (`db.local.sqlite3`) and uploads in `media-local/`. Both are ignored by Git. Keep a backup if you need to preserve local data. Existing server databases and `test.sqlite3` are separate. Email messages appear in the backend console. Celery tasks run immediately; scheduled tasks require a separately configured worker, scheduler, and Redis. External services such as SMS, Google login, and AI require their own credentials.

Django 5.2.8 or newer in the 5.2 series supports Python 3.14 and the constraint syntax used by existing migrations. The `django-mptt` package supplies the `mptt` module; Google authentication includes its Requests transport dependency.

## Install the frontend

In a second PowerShell terminal:

```powershell
cd '..\..\kavehmetal front'
npm.cmd ci
```

Create `.env.local` in the frontend repository with:

```dotenv
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
NEXT_PUBLIC_SITE_URL=http://localhost:3000
CANONICAL_SITE_URL=http://localhost:3000
```

Then run `npm.cmd run dev` and open http://localhost:3000. Keep both backend and frontend terminals running.

## Verify

```powershell
.\.venv\Scripts\python.exe manage.py check --settings=tg1.settings_local
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=tg1.settings_test
.\.venv\Scripts\python.exe manage.py test --settings=tg1.settings_test
```

In the frontend repository: `npm.cmd run test:seo`, `npm.cmd run lint`, and `npm.cmd run build`.

## Sync

Both repositories use `dev-ariakhayer`, tracking `origin/dev-ariakhayer`. In each repository, run `git pull --ff-only` before working. After reviewing and committing source changes, run `git push`. Local environments, secrets, dependencies, and development data stay out of commits.
