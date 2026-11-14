# Database connections

Two psycopg connections, with independent SQL version histories.
Default deployment uses APP_DB_PASSWORD / IMAGE_DB_PASSWORD plus service DNS names.
Tests can override full connection URLs to isolated databases.
No cross-database foreign keys or distributed atomic commit is assumed.
The API checks committed image availability when completing a Trip.
