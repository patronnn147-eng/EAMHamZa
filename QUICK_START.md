# 🚀 Quick Start Guide - Docker Setup

Get the entire Asset Management System running in **under 5 minutes**!

## Prerequisites

✅ Docker Desktop installed ([Download here](https://www.docker.com/products/docker-desktop))

That's it! No need to install Python, Node.js, PostgreSQL, or anything else.

## Step 1: Start Everything

Open a terminal in the project root and run:

```bash
# Using Docker Compose directly
docker-compose --env-file .env.docker up -d
```

Or if you have `make` installed:

```bash
make up
```

## Step 2: Wait for Services to Start

The first time will take 2-3 minutes to download images and build containers.

Check status:
```bash
docker-compose ps
```

Wait until all services show "healthy" status.

## Step 3: Access the Application

Open your browser and go to:

**Frontend:** http://localhost:3000

## Step 4: Create Your First User

1. Click the **"Inscription"** tab
2. Fill in the registration form:
   - **Email:** your.email@example.com
   - **Nom:** Your Full Name
   - **Rôle:** Select **ADMIN** for first user
   - **Mot de passe:** Create a strong password
   - **Confirmer:** Re-enter password
3. Click **"S'inscrire"**
4. You'll be automatically logged in! 🎉

## Step 5: Explore

### Main Application
- **Frontend:** http://localhost:3000
- **Dashboard:** View system metrics
- **Machines:** Manage equipment
- **Work Orders:** Track maintenance tasks

### Developer Tools
- **API Documentation:** http://localhost:8000/docs
- **pgAdmin (Database Manager):** http://localhost:5050
  - Email: admin@admin.com
  - Password: admin_secure_password_change_me

## Common Commands

```bash
# View logs
docker-compose logs -f

# Stop everything
docker-compose down

# Restart a service
docker-compose restart backend

# Rebuild after code changes
docker-compose up -d --build
```

## Troubleshooting

### Services won't start?

```bash
# Check what's running
docker-compose ps

# View logs
docker-compose logs
```

### Port already in use?

Edit `docker-compose.yml` and change the port:
```yaml
ports:
  - "3001:80"  # Change 3000 to 3001
```

### Need to reset everything?

```bash
# Stop and remove everything
docker-compose down -v

# Start fresh
docker-compose --env-file .env.docker up -d
```

## Next Steps

- Read [DOCKER_README.md](DOCKER_README.md) for detailed documentation
- Configure production settings in `.env.docker`
- Set up database backups
- Deploy to production

## Need Help?

Check the [DOCKER_README.md](DOCKER_README.md) for:
- Detailed troubleshooting
- Production deployment guide
- Database management
- Development workflow

---

**That's it!** You now have a fully functional Asset Management System running with:
- ✅ React Frontend
- ✅ FastAPI Backend
- ✅ PostgreSQL Database
- ✅ pgAdmin Database Manager

All running in isolated Docker containers with automatic restarts and health checks. 🚀