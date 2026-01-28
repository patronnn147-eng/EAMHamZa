# Docker Setup Guide - Asset Management System

Complete Docker setup for running the entire Asset Management System with a single command.

## 📦 Services Included

1. **Backend API** (FastAPI) - Port 8000
2. **Frontend** (React) - Port 3000
3. **PostgreSQL Database** - Port 5432
4. **pgAdmin** (Database Management) - Port 5050

## 🚀 Quick Start

### Prerequisites

- Docker Desktop installed (includes Docker Compose)
- Git (to clone the repository)
- At least 4GB of available RAM

### One-Command Setup

```bash
# Navigate to project root
cd /workspace

# Start all services
docker-compose --env-file .env.docker up -d
```

That's it! All services will start automatically.

## 🔧 Configuration

### Environment Variables

Edit `/workspace/.env.docker` to customize:

```env
# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_secure_password_change_me
POSTGRES_DB=asset_management

# pgAdmin
PGADMIN_EMAIL=admin@admin.com
PGADMIN_PASSWORD=admin_secure_password_change_me

# Backend JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Frontend API URL
VITE_API_BASE_URL=http://localhost:8000
```

**⚠️ IMPORTANT:** Change all passwords before deploying to production!

## 📝 Usage

### Start Services

```bash
# Start all services in background
docker-compose --env-file .env.docker up -d

# Start with logs visible
docker-compose --env-file .env.docker up

# Start specific service
docker-compose --env-file .env.docker up -d backend
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes database data)
docker-compose down -v
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
docker-compose logs -f pgadmin
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Rebuild Services

```bash
# Rebuild all images
docker-compose build

# Rebuild specific service
docker-compose build backend

# Rebuild and start
docker-compose up -d --build
```

## 🌐 Access Points

Once all services are running:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Register new user |
| **Backend API** | http://localhost:8000 | - |
| **API Docs** | http://localhost:8000/docs | - |
| **pgAdmin** | http://localhost:5050 | Email: admin@admin.com<br>Password: (from .env.docker) |
| **PostgreSQL** | localhost:5432 | User: postgres<br>Password: (from .env.docker)<br>Database: asset_management |

## 🗄️ Database Management

### Using pgAdmin

1. Open http://localhost:5050
2. Login with credentials from `.env.docker`
3. Add new server:
   - **Name:** Asset Management DB
   - **Host:** postgres (service name, not localhost)
   - **Port:** 5432
   - **Username:** postgres (or from .env.docker)
   - **Password:** (from .env.docker)
   - **Database:** asset_management

### Using psql (Command Line)

```bash
# Connect to database
docker exec -it asset_management_db psql -U postgres -d asset_management

# Common commands
\dt          # List tables
\d+ table    # Describe table
\q           # Quit
```

### Database Backup

```bash
# Backup database
docker exec asset_management_db pg_dump -U postgres asset_management > backup.sql

# Restore database
docker exec -i asset_management_db psql -U postgres asset_management < backup.sql
```

## 🔍 Troubleshooting

### Check Service Status

```bash
docker-compose ps
```

### Check Service Health

```bash
docker-compose ps
# Look for "healthy" status
```

### Common Issues

#### 1. Port Already in Use

**Error:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution:**
```bash
# Find process using the port
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "8001:8000"  # Use different external port
```

#### 2. Database Connection Failed

**Error:** Backend can't connect to database

**Solution:**
```bash
# Check if postgres is healthy
docker-compose ps postgres

# View postgres logs
docker-compose logs postgres

# Restart postgres
docker-compose restart postgres
```

#### 3. Frontend Can't Reach Backend

**Error:** API calls fail from frontend

**Solution:**
- Check `VITE_API_BASE_URL` in `.env.docker`
- Should be `http://localhost:8000` for local development
- Rebuild frontend after changing: `docker-compose up -d --build frontend`

#### 4. Permission Denied

**Error:** Permission errors in containers

**Solution:**
```bash
# Fix volume permissions
docker-compose down
docker volume rm workspace_postgres_data workspace_pgadmin_data
docker-compose up -d
```

#### 5. Out of Memory

**Error:** Services crash or become unresponsive

**Solution:**
- Increase Docker Desktop memory limit (Settings > Resources)
- Recommended: 4GB minimum, 8GB preferred

### View Container Details

```bash
# Inspect container
docker inspect asset_management_backend

# Enter container shell
docker exec -it asset_management_backend /bin/sh

# Check container resources
docker stats
```

## 🔄 Development Workflow

### Making Code Changes

#### Backend Changes

```bash
# After changing backend code
docker-compose restart backend

# Or rebuild if dependencies changed
docker-compose up -d --build backend
```

#### Frontend Changes

```bash
# After changing frontend code
docker-compose up -d --build frontend
```

### Database Migrations

```bash
# Create migration
docker exec -it asset_management_backend alembic revision --autogenerate -m "description"

# Apply migrations
docker exec -it asset_management_backend alembic upgrade head

# Rollback migration
docker exec -it asset_management_backend alembic downgrade -1
```

## 🧹 Cleanup

### Remove All Containers and Images

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (⚠️ deletes all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Complete cleanup
docker system prune -a --volumes
```

## 📊 Monitoring

### Resource Usage

```bash
# Real-time resource monitoring
docker stats

# Disk usage
docker system df
```

### Logs Management

```bash
# Limit log size in docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## 🚀 Production Deployment

### Security Checklist

- [ ] Change all default passwords in `.env.docker`
- [ ] Use strong JWT secret key (64+ random characters)
- [ ] Enable HTTPS (use reverse proxy like Nginx/Traefik)
- [ ] Set `ENVIRONMENT=production`
- [ ] Disable debug mode
- [ ] Configure firewall rules
- [ ] Set up regular database backups
- [ ] Enable Docker secrets instead of environment variables
- [ ] Implement rate limiting
- [ ] Set up monitoring and alerting

### Using Docker Secrets (Production)

```yaml
# docker-compose.prod.yml
secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
  jwt_secret:
    file: ./secrets/jwt_secret.txt

services:
  postgres:
    secrets:
      - postgres_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## 🆘 Support

If you encounter issues:

1. Check logs: `docker-compose logs -f`
2. Verify all services are healthy: `docker-compose ps`
3. Review this troubleshooting guide
4. Check Docker Desktop resources
5. Restart Docker Desktop if needed

## 📝 Notes

- **Data Persistence:** Database data is stored in Docker volumes and persists across restarts
- **Networking:** All services communicate through a dedicated Docker network
- **Health Checks:** Services have health checks to ensure they're running correctly
- **Auto-Restart:** Services automatically restart on failure
- **Multi-Stage Builds:** Frontend and backend use optimized multi-stage builds