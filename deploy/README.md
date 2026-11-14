# HTTPS deployment

Set SITE_ADDRESS in .env to a domain you control, for example loading.example.com (no https:// prefix).
Configure DNS and network access for Caddy certificate issuance; clients must trust the resulting certificate.
Run: docker compose -f compose.yaml -f compose.https.yaml up --build -d
Use https://YOUR-DOMAIN. Restrict the development port 8080 at the server firewall on production hosts.
For internal-only deployments use your organization's trusted TLS certificate/reverse proxy instead; do not bypass browser certificate warnings.
The two database services are never published to host ports.
