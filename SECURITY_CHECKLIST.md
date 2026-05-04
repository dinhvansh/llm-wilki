# Security Checklist

Minimum checks before any non-local deployment:

- Change `SECRET_KEY`.
- Disable or rotate the seeded dev admin credentials.
- Use strong database and Redis credentials.
- Restrict CORS origins to trusted frontend hosts.
- Store API keys in environment variables or a secret manager.
- Require HTTPS at the reverse proxy/load balancer.
- Verify uploaded file size limits and storage quotas.
- Back up PostgreSQL and upload storage before migrations.
- Review admin/audit access and confirm only `admin` users can access `/api/admin/*`.
- Run Docker smoke and E2E smoke against the deployment candidate.
