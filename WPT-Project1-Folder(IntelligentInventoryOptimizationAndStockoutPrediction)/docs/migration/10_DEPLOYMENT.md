# 🚀 Deployment Guide

> **Tujuan**: Deploy Flask + Next.js ke production
> 
> **Level**: Opsional (untuk setelah development selesai)

---

## 📦 Option 1: Docker (Recommended untuk Production)

### Struktur Docker

```
WPT-Project1-Folder/
├── docker-compose.yml      # Orchestration
├── backend/
│   └── Dockerfile          # Flask image
├── frontend/
│   └── Dockerfile          # Next.js image
└── nginx/
    └── nginx.conf          # Reverse proxy
```

### `docker-compose.yml`

```yaml
version: '3.8'

services:
  # Flask Backend
  backend:
    build: ./backend
    container_name: inventory-api
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - DATABASE_URL=sqlite:///./app.db
    volumes:
      - ./data:/app/data  # Mount data folder
    restart: unless-stopped

  # Next.js Frontend
  frontend:
    build: ./frontend
    container_name: inventory-web
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:5000/api
    depends_on:
      - backend
    restart: unless-stopped

  # Nginx Reverse Proxy (Optional)
  nginx:
    image: nginx:alpine
    container_name: inventory-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - frontend
      - backend
    restart: unless-stopped
```

### `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "run:app"]
```

### `frontend/Dockerfile`

```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Production image
FROM node:18-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000

CMD ["npm", "start"]
```

### Run dengan Docker

```powershell
# Build dan jalankan semua services
docker-compose up --build -d

# Lihat logs
docker-compose logs -f

# Stop semua
docker-compose down
```

---

## 🖥️ Option 2: Local Development (No Docker)

### Terminal 1: Backend

```powershell
cd backend
.\venv\Scripts\Activate
python run.py
# → http://localhost:5000
```

### Terminal 2: Frontend

```powershell
cd frontend
npm run dev
# → http://localhost:3000
```

---

## ☁️ Option 3: Cloud Deployment (Gratis)

### Backend: Railway / Render

1. Push ke GitHub
2. Connect repository di [Railway](https://railway.app) atau [Render](https://render.com)
3. Set environment variables
4. Deploy!

### Frontend: Vercel

1. Push ke GitHub
2. Import di [Vercel](https://vercel.com)
3. Set `NEXT_PUBLIC_API_URL` ke URL backend
4. Deploy!

---

## 🔧 Environment Variables (Production)

### Backend `.env.production`

```env
FLASK_ENV=production
SECRET_KEY=generate-strong-secret-key-here
JWT_SECRET_KEY=generate-jwt-secret-here
DATABASE_URL=postgresql://user:pass@host/db
CORS_ORIGINS=https://yourdomain.com
```

### Frontend `.env.production`

```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

---

## ✅ Production Checklist

- [ ] Change all secret keys
- [ ] Enable HTTPS
- [ ] Set up database backups
- [ ] Configure logging
- [ ] Set up monitoring (optional)
- [ ] Test all functionality

---

## 🎉 Selesai!

Anda telah menyelesaikan panduan migrasi lengkap dari Streamlit ke Flask API + Next.js!

**Langkah selanjutnya untuk vibe coder:**
1. Mulai dari [02_FLASK_API_SETUP.md](./02_FLASK_API_SETUP.md) untuk setup backend
2. Minta bantuan untuk implementasi setiap bagian
3. Test secara incremental
4. Deploy setelah semua berjalan!
