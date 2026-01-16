# 📚 Panduan Migrasi: Streamlit → Flask API + Next.js

> **Target Audience**: Vibe Coders yang terbiasa dengan Python/Streamlit
> 
> **Waktu Estimasi**: 2-4 minggu (dengan AI assistance)

---

## 🎯 Quick Start

```powershell
# Setelah migrasi selesai, cara menjalankan:

# Terminal 1: Backend Flask
cd backend
python app.py
# → http://localhost:5000

# Terminal 2: Frontend Next.js  
cd frontend
npm run dev
# → http://localhost:3000 (buka di browser)
```

---

## 📋 Daftar Panduan (Urutan Pengerjaan)

| No | Dokumen | Deskripsi | Prioritas |
|----|---------|-----------|-----------|
| 01 | [Project Overview](./01_PROJECT_OVERVIEW.md) | Analisis arsitektur saat ini | 🔴 Wajib Baca |
| 02 | [Flask API Setup](./02_FLASK_API_SETUP.md) | Setup project Flask backend | 🔴 Step 1 |
| 03 | [API Endpoints Design](./03_API_ENDPOINTS_DESIGN.md) | Desain REST API endpoints | 🔴 Step 2 |
| 04 | [Auth Migration](./04_AUTH_MIGRATION.md) | Migrasi sistem autentikasi | 🟡 Step 3 |
| 05 | [Data Layer Migration](./05_DATA_LAYER_MIGRATION.md) | Migrasi data loader & services | 🟡 Step 4 |
| 06 | [Business Logic Migration](./06_BUSINESS_LOGIC_MIGRATION.md) | Migrasi ML pipeline & analytics | 🟡 Step 5 |
| 07 | [Frontend Setup](./07_FRONTEND_SETUP.md) | Setup Next.js + TailwindCSS | 🔴 Step 6 |
| 08 | [UI Components](./08_UI_COMPONENTS.md) | Pembuatan komponen React | 🟡 Step 7 |
| 09 | [State Management](./09_STATE_MANAGEMENT.md) | Session state → React state | 🟢 Step 8 |
| 10 | [Deployment](./10_DEPLOYMENT.md) | Docker & deployment options | 🟢 Opsional |
| **11** | [**Design System**](./11_DESIGN_SYSTEM.md) | **Fintech Neumorphism UI/UX** | **🔴 Reference** |

**Legend**: 🔴 Critical | 🟡 Important | 🟢 Optional

---

## 🏗️ Arsitektur Target

```
┌─────────────────────────────────────────────────────────────┐
│                        BROWSER                               │
│                   http://localhost:3000                      │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP Requests
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  Dashboard  │ │ Forecasting │ │   Alerts    │   ...      │
│  │    Page     │ │    Page     │ │    Page     │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌──────────────────────────────────────────────┐           │
│  │           React Components + TailwindCSS      │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST API (JSON)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (Flask API)                       │
│                   http://localhost:5000                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    API Endpoints                     │    │
│  │  /api/auth  /api/dashboard  /api/forecasting  ...   │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   Business Logic                     │    │
│  │  ML Pipeline │ Data Loader │ Analytics Services     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                              │
│              CSV Files / SQLite / PostgreSQL                 │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Prerequisites Checklist

Sebelum memulai migrasi, pastikan sudah terinstall:

### Backend (Python)
- [ ] Python 3.10+
- [ ] pip (package manager)
- [ ] Virtual environment (venv)

### Frontend (Node.js)
- [ ] Node.js 18+ ([Download](https://nodejs.org/))
- [ ] npm (terinstall bersama Node.js)

### Tools
- [ ] Git
- [ ] VS Code (dengan extensions: Python, ESLint, Prettier)

---

## 🚀 Langkah Pertama

Mulai dari **[01_PROJECT_OVERVIEW.md](./01_PROJECT_OVERVIEW.md)** untuk memahami arsitektur saat ini sebelum migrasi.

---

## 📞 Bantuan

Sebagai **vibe coder**, Anda bisa meminta bantuan kapan saja untuk:
- Menjelaskan konsep yang tidak dipahami
- Menulis code untuk komponen tertentu
- Debugging error yang muncul
- Review dan optimasi code

> **Tip**: Copy-paste error message lengkap untuk mendapat bantuan yang lebih akurat!
