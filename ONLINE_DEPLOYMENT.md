# HRD Tools — Online deployment (Streamlit Cloud + PostgreSQL)

This branch is focused on the online application. LAN/offline synchronization is intentionally out of scope for this release.

## Architecture

- Streamlit Community Cloud hosts the web application.
- A managed PostgreSQL database (for example Neon or Supabase) stores HRD records persistently.
- The database connection string is stored in Streamlit Cloud Secrets, never committed to Git.
- PostgreSQL schema is defined in `migrations/postgres/001_online_schema.sql`.

**Do not use the SQLite fallback for production.** It is intended only for local development and may not provide durable storage on a hosted app filesystem.

## One-time database setup

1. Create a PostgreSQL database with a managed provider.
2. Require SSL/TLS for database connections.
3. Open the provider's SQL editor or connect using `psql`.
4. Run the complete file `migrations/postgres/001_online_schema.sql` against the empty database.
5. Keep database network access restricted where the provider supports it. Do not expose credentials in GitHub issues, commits, or chat.

## Streamlit Community Cloud setup

In Streamlit Community Cloud, open the app's **Settings → Secrets** and add:

```toml
DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"

[users]
niko = "UNIQUE_STRONG_PASSWORD"
agung = "UNIQUE_STRONG_PASSWORD"
iis = "UNIQUE_STRONG_PASSWORD"
nurhayat = "UNIQUE_STRONG_PASSWORD"
"23010202" = "UNIQUE_STRONG_PASSWORD"
"26090328" = "UNIQUE_STRONG_PASSWORD"
"26092377" = "UNIQUE_STRONG_PASSWORD"
```

Use a different strong password for every account. Replace all placeholders before saving. Do not commit the real Secrets file.

The app creates initial accounts and stores salted PBKDF2 password hashes. All initial accounts are required to use passwords. If a user already has a password hash in the database, the app does not overwrite it with the bootstrap value. New accounts can be managed by the Super Admin from the app.

After saving Secrets, reboot the Streamlit app. Verify that it connects to PostgreSQL and that the app can add, edit, read, and export records.

## Initial accounts

The usernames are seeded by the application:
- `niko` — Super Admin
- `agung`, `iis`, `nurhayat` — Admin HRD
- `23010202`, `26090328`, `26092377` — Tally Shift E/F/G

Passwords must be configured in Streamlit Secrets before first login. If bootstrap passwords are missing, initial accounts remain password-locked; this is intentional and safer than passwordless internet access.

## Acceptance checklist before operational use

- [ ] PostgreSQL schema migration completed successfully.
- [ ] Streamlit Secrets contain the PostgreSQL DSN and unique initial passwords.
- [ ] App starts without a database connection error.
- [ ] Each role can log in with its own password.
- [ ] Super Admin can add/edit users and permissions.
- [ ] Master employee import and update works.
- [ ] Attendance, SP, H3 evaluation, non-renewal, calls, history, and Excel export work.
- [ ] A record remains after app reboot and a second browser session.
- [ ] Database backup and restore are configured with the database provider.

## Important

The repository changes do not provision a database provider, set Streamlit Cloud Secrets, or change the active Streamlit deployment. Those actions require access to the user's provider and Streamlit Cloud accounts. Do not treat the app as production-ready until the acceptance checklist is completed.
