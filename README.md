# \# Smart Greenhouse

# 

# Smart Greenhouse is a three-tier application created for the Design Patterns 2026 course.

# 

# Phase 1 establishes the project foundation with:

# 

# \- FastAPI backend

# \- PostgreSQL database

# \- SQLAlchemy and Alembic migration tooling

# \- React + TypeScript frontend

# \- Vite

# \- Tailwind CSS v4

# \- Scalar API documentation

# 

# No business entities or design patterns are implemented in Phase 1.

# 

# \## Prerequisites

# 

# Install the following tools before running the project:

# 

# \- Python 3.11+

# \- Node.js 20 LTS

# \- Docker Desktop

# \- Git

# 

# \## Project Structure

# 

# ```text

# design-patterns-2026/

# ├── backend/

# ├── frontend/

# ├── database/

# ├── docker-compose.yml

# ├── .env.example

# └── README.md

# ```

# 

# \## Initial Setup

# 

# \### 1. Environment variables

# 

# From the project root, copy the example environment file:

# 

# ```powershell

# Copy-Item .env.example .env

# ```

# 

# The `.env` file is local configuration and must not be committed to Git.

# 

# \### 2. Start PostgreSQL

# 

# From the project root:

# 

# ```powershell

# docker compose up -d

# ```

# 

# Check the database status:

# 

# ```powershell

# docker compose ps

# ```

# 

# PostgreSQL should report a healthy status.

# 

# \### 3. Backend setup

# 

# Move to the backend directory:

# 

# ```powershell

# cd backend

# ```

# 

# Create a virtual environment:

# 

# ```powershell

# python -m venv .venv

# ```

# 

# Activate it on Windows PowerShell:

# 

# ```powershell

# .\\.venv\\Scripts\\Activate.ps1

# ```

# 

# Install the backend and development dependencies:

# 

# ```powershell

# python -m pip install -e ".\[dev]"

# ```

# 

# Apply database migrations:

# 

# ```powershell

# python -m alembic upgrade head

# ```

# 

# Start the API:

# 

# ```powershell

# python -m uvicorn src.main:app --reload

# ```

# 

# \### 4. Frontend setup

# 

# Move to the frontend directory:

# 

# ```powershell

# cd frontend

# ```

# 

# Install dependencies:

# 

# ```powershell

# npm install

# ```

# 

# Copy the frontend environment configuration:

# 

# ```powershell

# Copy-Item .env.example .env

# ```

# 

# Start the frontend:

# 

# ```powershell

# npm run dev

# ```

# 

# \## Daily Start

# 

# Start PostgreSQL from the project root:

# 

# ```powershell

# docker compose up -d

# ```

# 

# Start the backend from the `backend` directory:

# 

# ```powershell

# .\\.venv\\Scripts\\Activate.ps1

# python -m uvicorn src.main:app --reload

# ```

# 

# Start the frontend from the `frontend` directory:

# 

# ```powershell

# npm run dev

# ```

# 

# \## Application URLs

# 

# When using the default configuration:

# 

# \- Frontend: `http://localhost:5173`

# \- API: `http://127.0.0.1:8000`

# \- Health endpoint: `http://127.0.0.1:8000/health`

# \- Scalar API reference: `http://127.0.0.1:8000/scalar`

# 

# Swagger UI at `/docs` and ReDoc are disabled.

# 

# \## Database Migrations

# 

# Alembic manages database migrations.

# 

# Check the current revision:

# 

# ```powershell

# cd backend

# python -m alembic current

# ```

# 

# Phase 1 contains an empty baseline migration. It creates no Smart Greenhouse business tables. PostgreSQL contains the `alembic\_version` table for migration tracking.

# 

# \## Phase Documentation

# 

# See \[docs/phases/README.md](docs/phases/README.md) for information about the project phases.

