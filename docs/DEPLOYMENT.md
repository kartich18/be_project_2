# Deployment Guide
This guide provides instructions for deploying the Quantum-Safe Banking API behind a production-grade Nginx reverse proxy using Gunicorn and securing it with Let's Encrypt (Certbot).

## 1. Install Dependencies
Install Nginx, Certbot, and Python requirements on your production server:
```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

Ensure your Python environment contains `gunicorn`:
```bash
pip install -r requirements.txt
```

## 2. Nginx Configuration
Copy the provided Nginx configuration to your server's Nginx setup. Ensure you replace `example.com` with your actual domain name.

```bash
sudo cp docs/nginx.conf /etc/nginx/sites-available/quantum-bank
sudo ln -s /etc/nginx/sites-available/quantum-bank /etc/nginx/sites-enabled/
```

Verify the configuration is correct:
```bash
sudo nginx -t
```

Reload Nginx:
```bash
sudo systemctl reload nginx
```

## 3. Obtain TLS Certificates
Use Certbot to request Let's Encrypt certificates. The python3-certbot-nginx plugin will automatically apply them if you used the domain correctly. Run:

```bash
sudo certbot --nginx -d example.com -d www.example.com
```

Certbot will automatically renew certificates. You can test the renewal process:
```bash
sudo certbot renew --dry-run
```

Ensure you no longer use `scripts/generate_certs.py` in production as it generates untrusted self-signed certificates.

## 4. Run Gunicorn
Start the Flask application using Gunicorn. You can manage this with `systemd` or run it inside a screen/tmux session temporarily.

```bash
# Example running with 4 workers:
gunicorn -w 4 -b 127.0.0.1:5000 "app:create_app()"
```

Note: The database configuration (`DATABASE_URL`) should be passed as an environment variable to point to your NeonDB PostgreSQL instance instead of the local SQLite fallback.

```bash
export DATABASE_URL="postgresql://user:password@hostname/dbname"
gunicorn -w 4 -b 127.0.0.1:5000 "app:create_app()"
```
