# Agro Z — Smart Agriculture Advisory Dashboard

A Flask-based college project connecting soil analysis, crop recommendation, fertilizer advisory, live weather and Indian mandi-market intelligence.

## What was upgraded
- Persistent database layer using Flask-SQLAlchemy.
- Local SQLite for easy development, PostgreSQL/Supabase through `DATABASE_URL` for deployment.
- User, soil, recommendation, weather-history and market-history records.
- Admin analytics dashboard.
- Better responsive UI while preserving the original dark/deep-green Agro Z palette.
- OpenWeather current weather + 5-day forecast integration.
- Public AGMARKNET 2.0 backend integration with a clearly-labelled demo fallback.
- Production server support through Gunicorn.
- Render deployment blueprint included.
- Optional future Random Forest model loader/training path remains separate from the safe compatibility fallback.

## Run locally on Windows
```cmd
D:
cd Agro-Z-Complete
python -m pip install -r requirements.txt
set OPENWEATHER_API_KEY=YOUR_KEY
set AGROZ_SECRET_KEY=change-this-to-a-long-random-value
python app.py
```
Open `http://127.0.0.1:5000`.

If no `DATABASE_URL` is set, SQLite is used automatically and the database is created as `agro_z.db`.

## Demo admin
- Email: `admin@agroz.local`
- Password: `admin123`

For deployment, set `AGROZ_ADMIN_PASSWORD` to a new password before the first startup.

## Weather
Set `OPENWEATHER_API_KEY`. Never commit the key to GitHub. Put it in Render/Supabase environment configuration instead.

## Market
The market service attempts the public AGMARKNET 2.0 backend at `api.agmarknet.gov.in/v1` and falls back to development values if the upstream service is unavailable. The UI always tells the user whether values are live or fallback.

## Database / hosting
For a persistent hosted database, create a free Supabase Postgres project and copy its connection string into `DATABASE_URL`. Supabase currently offers a Free plan with a 500 MB database quota. Free projects can pause after inactivity, so this is suitable for a college demo rather than a production SLA.

Render can host the Flask web service for free. Its free web services spin down after 15 minutes idle. Render's free Postgres is not used by this blueprint because it currently expires after 30 days. Use Supabase Postgres for a longer-lived student demo database.

## ML note
The current recommendation engine is a transparent agronomy compatibility fallback so the application works without inventing a model accuracy claim. When a real labelled dataset is available, add a validated Random Forest model and replace the fallback in `services/recommendation.py`. Do not display a percentage as model accuracy unless it comes from a reproducible validation result.


## Supabase verification
The app now explicitly loads the local `.env` before configuring SQLAlchemy.
After starting the app, open `/health` to verify `database_backend` is `postgresql`.
While logged in, open `/api/db-check` to verify counts for the current account.
If `database_backend` says `sqlite`, the app is not reading `DATABASE_URL`.
