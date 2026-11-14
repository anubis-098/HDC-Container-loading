# Business database

`001_initial.sql` creates workers/admins/sessions, stores, trips, shipments, pallets, photo references and audit_log.
`python -m app.migrate` applies ordered SQL files once using schema_migrations and an advisory lock.
Add new numbered SQL files for subsequent schema changes; never edit a migration already applied to a deployment.
