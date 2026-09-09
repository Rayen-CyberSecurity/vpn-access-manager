# VPN Access Manager

Term project for **Introduction to Database Management Systems** at THGA Bochum.

The application manages VPN users, gateways and VPN sessions using a PostgreSQL database, a FastAPI REST API and a tkinter desktop client.

## Project Structure

```text
vpn-access-manager/
├── api/                    FastAPI backend
├── db/                     PostgreSQL schema and seed data
├── frontend/               tkinter desktop client
├── tests/                  pytest test suite
├── docs/                   LaTeX documentation and screenshots
├── docker-compose.yml      PostgreSQL + API services
├── Dockerfile              API container
├── requirements.txt        Python dependencies
└── Makefile                Documentation build
```

## Requirements

To run the database and API:

- Docker
- Docker Compose

To run the desktop client from source:

- Python
- tkinter
- uv
- Python dependencies from `requirements.txt`

## 1. Start Database and API

From the project directory:

```bash
docker compose up -d --build
```

Check that the containers are running:

```bash
docker compose ps
```

The REST API is available at:

```text
http://localhost:8000
```

Interactive FastAPI documentation:

```text
http://localhost:8000/docs
```

## 2. API Authentication

Read operations do not require authentication.

Write operations require the following HTTP header:

```text
X-API-Key: dev-key
```

The development API key is configured for local project testing.

## 3. REST API

The project implements five REST operations:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/gateways` | List gateways and active session counts |
| GET | `/sessions` | List and filter sessions |
| GET | `/sessions/{id}` | Show one session |
| POST | `/sessions` | Open a new VPN session |
| POST | `/sessions/{id}/close` | Close a VPN session |

Session listing supports the optional `status` and `gateway` filters.

Example:

```text
GET /sessions?status=active&gateway=gw-eu-1
```

## 4. Run the Desktop Client

Install the Python dependencies:

```bash
uv pip install -r requirements.txt
```

Run the frontend:

```bash
uv run python frontend/app.py
```

In the connection dialog use:

```text
API URL: http://localhost:8000
API Key: dev-key
```

The desktop application communicates only with the REST API and does not access PostgreSQL directly.

## 5. Run the Tests

With the Docker services running:

```bash
uv run pytest -q
```

The test suite covers the database/API acceptance criteria, including authentication, filtering, gateway capacity and session closing.

## 6. Reset the Database

To recreate the database from `db/init.sql`:

```bash
docker compose down -v
docker compose up -d --build
```

This removes the PostgreSQL volume and initializes a clean database with the supplied seed data.

## 7. Build the Debian Package

The desktop client can be packaged as a Debian package using PyInstaller and fpm.

Install PyInstaller if necessary:

```bash
uv pip install pyinstaller
```

Then build:

```bash
uv run bash frontend/packaging/build-deb.sh
```

The resulting package is:

```text
vpn-manager_0.1.0_amd64.deb
```

It can be installed on a compatible Debian/Ubuntu system with:

```bash
sudo apt install ./vpn-manager_0.1.0_amd64.deb
```

The installed desktop application can then be started with:

```bash
vpn-manager
```

## 8. Documentation

Build the user manual and developer documentation with:

```bash
make
```

The generated PDFs are written to:

```text
out/user-manual.pdf
out/developer-doc.pdf
```

## Stop the Application

Stop the Docker services with:

```bash
docker compose down
```

To also delete the database volume:

```bash
docker compose down -v
```

## Author

Rayen Ben Haj Rhouma
Introduction to Database Management Systems
THGA Bochum
