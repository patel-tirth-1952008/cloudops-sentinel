# CloudOps Sentinel - Real-Time Infrastructure Health & Incident Monitor

[![Continuous Integration](https://github.com/patel-tirth-1952008/cloudops-sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/patel-tirth-1952008/cloudops-sentinel/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14.1.0-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

> Production-grade microservices health monitor and automated incident alerting engine with latency anomaly detection, uptime SLAs, and webhook notifications.

---

## 🏛️ System Architecture

```
                                  +-----------------------------+
                                  |    Next.js 14 App Router    |
                                  |  (TypeScript + Tailwind)    |
                                  +--------------+--------------+
                                                 |
                                                 | HTTP / JSON
                                                 v
                                  +--------------+--------------+
                                  |     FastAPI Backend API     |
                                  |   (Pydantic + In-Memory DB) |
                                  +--------------+--------------+
                                                 |
                                        +--------+--------+
                                        |                 |
                                        v                 v
                               +----------------+  +----------------+
                               | Health Monitor |  |  CRUD Engine   |
                               +----------------+  +----------------+
```

---

## ✨ Features

- **Production-Ready FastAPI Backend**: Full schema validation with Pydantic v2, CORS support, comprehensive error handling, and pre-seeded realistic data.
- **Modern Next.js 14 Dashboard**: Dark-mode UI styled with Tailwind CSS, responsive state management, and real-time backend API consumption.
- **Automated Pytest Suite**: Complete unit and integration test coverage executing against FastAPI's TestClient.
- **One-Command Dockerization**: Multi-stage Dockerfiles and docker-compose.yml for unified local setup.
- **GitHub Actions CI Pipeline**: Automated build and test verification on every commit.

---

## 🔌 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | System health and database connectivity probe |
| `GET` | `/api/services` | List all monitored services with real-time status and uptime percentage |
| `POST` | `/api/services` | Register a new service with healthcheck URL and threshold parameters |
| `GET` | `/api/services/{service_id}/metrics` | Retrieve latency, error rate, and CPU metrics time series |
| `POST` | `/api/incidents` | Trigger and log a new incident with severity level |
| `GET` | `/api/incidents` | List active and resolved incidents with audit log |
| `PATCH` | `/api/incidents/{incident_id}/resolve` | Acknowledge and resolve an active incident |

---

## 🚀 Quick Start

### 1. Run with Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/patel-tirth-1952008/cloudops-sentinel.git
cd cloudops-sentinel

# Spin up both frontend and backend
docker-compose up --build
```

- **Frontend Application**: `http://localhost:3000`
- **FastAPI Interactive Docs**: `http://localhost:8000/docs`
- **Backend Health Check**: `http://localhost:8000/api/health`

---

### 2. Run Manually (Local Development)

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

#### Run Tests
```bash
cd backend
pytest -v
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 📂 Project Structure

```
.
├── .github/
│   └── workflows/
│       └── ci.yml                 # Automated Pytest CI workflow
├── backend/
│   ├── main.py                    # FastAPI application & business logic
│   ├── test_main.py               # Comprehensive Pytest test suite
│   ├── requirements.txt           # Python dependencies
│   └── Dockerfile                 # Backend container definition
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── globals.css        # Tailwind base styles
│   │       ├── layout.tsx         # Next.js Root Layout with header
│   │       └── page.tsx           # Interactive client dashboard
│   ├── package.json               # Node.js dependencies
│   ├── tsconfig.json              # TypeScript configuration
│   ├── tailwind.config.js         # Tailwind configuration
│   ├── next.config.js             # Next.js configuration
│   └── Dockerfile                 # Frontend container definition
├── docker-compose.yml             # Orchestration for both services
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git ignore rules
└── README.md                      # Comprehensive project documentation
```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
