# Installation Guide - Asset Management System

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- pnpm (or npm)

## Backend Setup

### 1. Navigate to Backend Directory
```bash
cd app/backend
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
The `.env` file is already created with default values. For production, update:
```
JWT_SECRET_KEY=your-very-secure-random-key-here
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname  # For PostgreSQL
```

### 5. Initialize Database
The database will be automatically created on first run using SQLite.

For PostgreSQL setup:
1. Install PostgreSQL
2. Create database: `createdb asset_management`
3. Update `DATABASE_URL` in `.env`
4. Run migrations (if needed)

### 6. Start Backend Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs

## Frontend Setup

### 1. Navigate to Frontend Directory
```bash
cd app/frontend
```

### 2. Install Dependencies
```bash
pnpm install
# or
npm install
```

### 3. Configure Environment Variables
Create `.env` file in `app/frontend`:
```bash
VITE_API_BASE_URL=http://localhost:8000
```

### 4. Start Frontend Development Server
```bash
pnpm run dev
# or
npm run dev
```

Frontend will be available at: http://localhost:3000

## First User Registration

1. Open http://localhost:3000 in your browser
2. Click "Inscription" tab
3. Fill in the registration form:
   - Email: your.email@example.com
   - Nom: Your Full Name
   - Rôle: Select ADMIN for first user
   - Mot de passe: Create a strong password (min 8 chars, 1 uppercase, 1 lowercase, 1 number)
   - Confirmer le mot de passe: Re-enter password
4. Click "S'inscrire"
5. You'll be automatically logged in and redirected to the dashboard

## Database Information

The system uses **SQLite** by default for easy setup. The database file is created at `app/backend/app.db`.

### Database Schema

**utilisateurs** table:
- `id` (Integer, Primary Key, Auto-increment)
- `email` (String, Unique, Not Null) - User email for login
- `nom` (String, Not Null) - Full name
- `mot_de_passe` (String, Not Null) - Bcrypt hashed password
- `role` (Enum, Not Null) - User role: TECHNICIEN, CHEFTECH, CHETOP, ADMIN
- `created_at` (DateTime, Not Null) - Account creation timestamp

### Switching to PostgreSQL (Production)

1. Install PostgreSQL and asyncpg:
```bash
pip install asyncpg
```

2. Create database:
```bash
createdb asset_management
```

3. Update `.env`:
```
DATABASE_URL=postgresql+asyncpg://username:password@localhost/asset_management
```

4. Restart backend server

## Troubleshooting

### Backend Issues

**Error: "email-validator is not installed"**
```bash
pip install email-validator
```

**Error: "database_url not found"**
- Make sure `.env` file exists in `app/backend`
- Check that `DATABASE_URL` is set in `.env`

**Error: "passlib not found"**
```bash
pip install passlib[bcrypt]
```

### Frontend Issues

**Error: "Failed to load resource: 404"**
- Make sure backend is running on port 8000
- Check `VITE_API_BASE_URL` in frontend `.env`

**Error: "CORS error"**
- Backend already has CORS configured for localhost:3000
- If using different port, update CORS settings in `backend/main.py`

### Authentication Issues

**Cannot login after registration**
- Check backend logs for errors
- Verify password meets requirements (8+ chars, 1 uppercase, 1 lowercase, 1 number)
- Try registering with a different email

**Token expired**
- Tokens expire after 24 hours
- Simply login again to get a new token

## Production Deployment

### Backend

1. Set strong `JWT_SECRET_KEY` in production `.env`
2. Use PostgreSQL instead of SQLite
3. Set `ENVIRONMENT=production`
4. Use a production WSGI server (gunicorn + uvicorn workers):
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend

1. Update `VITE_API_BASE_URL` to production backend URL
2. Build for production:
```bash
pnpm run build
```
3. Serve the `dist` folder with nginx or similar

## Security Notes

1. **Change JWT_SECRET_KEY**: Use a strong random key in production
2. **Use HTTPS**: Always use HTTPS in production
3. **Database Backups**: Regularly backup your database
4. **Rate Limiting**: Consider adding rate limiting to prevent brute force attacks
5. **Environment Variables**: Never commit `.env` files to version control

## Support

For issues or questions:
1. Check the logs in `app/backend/logs/`
2. Review API documentation at http://localhost:8000/docs
3. Check `JWT_AUTHENTICATION_MIGRATION.md` for authentication details