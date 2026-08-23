# Vinayaka Festival Fund Manager

A Docker-based web application to manage Vinayaka Chaturthi festival donations, expenses, and fund balance with full transparency.

## Features

- **User accounts** — Register and login with username/password
- **Dashboard** — Live fund balance displayed prominently (Donations − Expenses)
- **Donations** — Record donor name, amount, phone, date, and notes
- **Expenses** — Record spending with categories and bill/receipt upload (PNG, JPG, PDF)
- **Reports** — Full summary with category breakdown and CSV export
- **Role-based access** — Read-only by default; admin grants write access
- **WhatsApp thank-you** — Telugu donation receipt via WhatsApp link
- **Activity log** — Tracks who added, edited, or deleted records

## Quick Start (Local Docker)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Steps

1. **Clone and enter the project**
   ```bash
   cd my-project
   ```

2. **Configure environment** (optional — defaults work for local testing)
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and change `SECRET_KEY` to a long random string before production.

3. **Build and run**
   ```bash
   docker compose up --build -d
   ```

4. **Open the app**
   ```
   http://localhost:8080
   ```

5. **Create your first account**
   - Click **Register** and create a committee member account
   - Login and start recording donations and expenses

### Stop the app

```bash
docker compose down
```

Data is preserved in Docker volumes (`festival_data`, `festival_uploads`).

### View logs

```bash
docker compose logs -f
```

## CI/CD — Auto deploy to GCP VM (GitHub Actions)

Every push to `main` automatically deploys to your GCP VM.

### One-time setup

#### 1. Prepare the GCP VM

SSH into your VM and run:

```bash
curl -fsSL https://raw.githubusercontent.com/sravan123-456/my-project/main/scripts/vm-setup.sh | bash
```

Or manually:

```bash
git clone https://github.com/sravan123-456/my-project.git ~/my-project
cd ~/my-project
cp .env.example .env
nano .env   # Set a strong SECRET_KEY
chmod +x scripts/*.sh
docker compose up --build -d
```

Open **port 8080** in GCP firewall (VPC network → Firewall → allow tcp:8080).

#### 2. Create SSH key for GitHub Actions

On your **local machine**:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f gcp_deploy_key -N ""
```

Add the **public** key to the VM:

```bash
ssh-copy-id -i gcp_deploy_key.pub YOUR_USER@YOUR_VM_IP
```

#### 3. Add GitHub repository secrets

Go to **GitHub → your repo → Settings → Secrets and variables → Actions** and add:

| Secret | Example | Description |
|--------|---------|-------------|
| `GCP_VM_HOST` | `34.123.45.67` | VM external IP address |
| `GCP_VM_USER` | `ubuntu` or your SSH username | Linux user on the VM |
| `GCP_VM_SSH_KEY` | contents of `gcp_deploy_key` | Private SSH key (entire file) |
| `GCP_VM_PORT` | `22` | Optional, defaults to 22 |

#### 4. Push to deploy

```bash
git push origin main
```

Check deployment status under **GitHub → Actions** tab.

Manual deploy from VM:

```bash
cd ~/my-project && ./scripts/deploy.sh
```

---

## Deploy on GCP Cloud VM (manual)

### 1. Create a VM

- Go to GCP Console → Compute Engine → Create Instance
- Machine type: `e2-micro` or `e2-small` (sufficient for committee use)
- Boot disk: Ubuntu 22.04 LTS, 20 GB
- Allow HTTP and HTTPS traffic (or open port 8080 in firewall)

### 2. SSH into the VM and install Docker

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
# Log out and back in for group change
```

### 3. Clone and deploy

```bash
git clone https://github.com/sravan123-456/my-project.git
cd my-project
cp .env.example .env
nano .env   # Set a strong SECRET_KEY
docker compose up --build -d
```

### 4. Access the app

Open `http://<VM_EXTERNAL_IP>:8080` in your browser.

### 5. (Optional) Use a domain with Nginx + HTTPS

For production, put Nginx in front with Let's Encrypt SSL. Example Nginx config:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 16M;
    }
}
```

## Project Structure

```
my-project/
├── app/
│   ├── models.py          # User, Donation, Expense models
│   ├── forms.py           # WTForms
│   ├── routes/            # Auth, dashboard, donations, expenses, reports
│   ├── templates/         # HTML templates
│   └── static/css/        # Festival-themed styles
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── run.py
└── .env.example
```

## Suggested Future Enhancements

| Feature | Benefit |
|---------|---------|
| **WhatsApp Business API** | Fully automated thank-you messages (no manual send) |
| **PDF report export** | Printable report for committee meetings |
| **Multi-year festivals** | Separate data per year (2024, 2025, etc.) |
| **Public transparency page** | Read-only balance visible to everyone (no login) |
| **Budget planning** | Set category budgets and alert when overspending |
| **Photo gallery** | Festival event photos alongside financial records |
| **UPI payment QR** | Display QR code for easy donations |

## Backup

Back up your data regularly:

```bash
# Export database volume
docker run --rm -v my-project_festival_data:/data -v $(pwd):/backup alpine tar czf /backup/festival-backup.tar.gz /data

# Export uploaded bills
docker run --rm -v my-project_festival_uploads:/uploads -v $(pwd):/backup alpine tar czf /backup/uploads-backup.tar.gz /uploads
```

## License

MIT — Free to use for community festivals.
