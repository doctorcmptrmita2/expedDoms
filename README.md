# ExpiredDomain.dev

Daily dropped domains explorer using ICANN CZDS zone files.

## Overview

ExpiredDomain.dev is a FastAPI-based web application that tracks dropped domains by comparing daily ICANN CZDS zone files. It identifies domains that were present yesterday but missing today, indicating expired or deleted registrations.

## Features

- **Daily Drop Detection**: Automatically compares zone files to identify dropped domains
- **Multi-TLD Support**: Track multiple top-level domains (configurable)
- **Web Interface**: Beautiful, modern UI built with Tailwind CSS
- **Search & Filter**: Filter dropped domains by date, TLD, length, charset type, and keyword search
- **RESTful API**: JSON API for programmatic access
- **Copy to Clipboard**: One-click domain copying

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: MySQL 8.x
- **ORM**: SQLAlchemy 2.x (sync)
- **Migrations**: Alembic
- **Templates**: Jinja2
- **Styling**: Tailwind CSS (CDN)
- **Server**: Uvicorn

## Installation

### Prerequisites

- Python 3.11 or higher
- MySQL 8.x
- pip

### Setup Steps

1. **Clone the repository** (or ensure you're in the project directory)

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
```

Edit `.env` and set:
- `DATABASE_URL`: Your MySQL connection string
- `TRACKED_TLDS`: Comma-separated list of TLDs to track (e.g., "zip,works,dev,app")
- `CZDS_USERNAME` and `CZDS_API_TOKEN` (optional - for automatic downloads)

5. **Create MySQL database**:
```sql
CREATE DATABASE expireddomain CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

6. **Run migrations**:
```bash
alembic upgrade head
```

7. **Create data directory structure**:
```bash
mkdir -p data/zones
```

## Usage

### Running the Web Application

Start the development server:
```bash
uvicorn app.main:app --reload
```

The application will be available at `http://localhost:8000`

### Daily Drop Detection Script

Run the daily script to fetch zone files and compute drops:

```bash
python -m scripts.fetch_drops
```

**For production**, set up a cron job to run this daily:
```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/project && /path/to/venv/bin/python -m scripts.fetch_drops
```

### Zone Files

The application needs zone files to compare. You have two options:

#### Option 1: Manual Download (Recommended for MVP)

1. Download zone files from ICANN CZDS manually
2. Place them in `data/zones/<tld>/YYYYMMDD.zone`
   - Example: `data/zones/zip/20250101.zone`

#### Option 2: Automatic Download via API

1. Get CZDS API credentials from ICANN
2. Set `CZDS_USERNAME` and `CZDS_API_TOKEN` in `.env`
3. The script will automatically download zone files

**Note**: The CZDS API integration includes TODO comments where exact endpoint/auth details may need adjustment based on ICANN's current API documentation.

## Project Structure

```
expireddomain/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── core/
│   │   ├── config.py        # Settings and configuration
│   │   └── database.py     # SQLAlchemy setup
│   ├── models/
│   │   ├── tld.py          # TLD model
│   │   └── drop.py         # DroppedDomain model
│   ├── schemas/
│   │   ├── tld.py          # Pydantic schemas for TLD
│   │   └── drop.py         # Pydantic schemas for drops
│   ├── services/
│   │   ├── czds_client.py  # CZDS API client
│   │   ├── zone_parser.py  # Zone file parser
│   │   └── drop_detector.py # Drop detection logic
│   ├── api/
│   │   └── v1/
│   │       ├── tlds.py     # TLD API endpoints
│   │       └── drops.py    # Drops API endpoints
│   └── web/
│       └── routes.py       # HTML page routes
├── templates/              # Jinja2 templates
├── static/                 # Static files (CSS, JS)
├── scripts/
│   └── fetch_drops.py     # Daily ingestion script
├── alembic/               # Database migrations
├── data/                  # Zone files storage
├── requirements.txt
├── .env.example
└── README.md
```

## API Endpoints

### TLDs

- `GET /api/v1/tlds` - List all tracked TLDs

### Drops

- `GET /api/v1/drops` - List dropped domains with filters
  - Query parameters:
    - `date` (optional): Filter by drop date (YYYY-MM-DD)
    - `tld` (optional): Filter by TLD name
    - `search` (optional): Search in domain names
    - `min_length` (optional): Minimum SLD length
    - `max_length` (optional): Maximum SLD length
    - `charset_type` (optional): Filter by charset (letters/numbers/mixed)
    - `page` (default: 1): Page number
    - `page_size` (default: 50, max: 200): Results per page

## Web Pages

- `/` - Home page with stats and preview
- `/drops` - Dropped domains list with filters
- `/tlds` - List of tracked TLDs
- `/about` - About page with information

## Database Schema

### tlds

- `id` (PK)
- `name` (unique)
- `display_name`
- `is_active`
- `last_import_date`
- `last_drop_count`
- `created_at`
- `updated_at`

### dropped_domains

- `id` (PK)
- `domain` (indexed)
- `tld_id` (FK → tlds.id)
- `drop_date` (indexed)
- `length` (SLD length)
- `label_count`
- `charset_type` (letters/numbers/mixed)
- `quality_score` (reserved)
- `created_at`
- Unique constraint: (domain, drop_date)

## Development

### Running Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback:
```bash
alembic downgrade -1
```

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to functions
- Keep functions focused and small

## Production Deployment

1. Set `ENV=production` in `.env`
2. Configure proper `DATABASE_URL` with production credentials
3. Set up nginx reverse proxy
4. Use a process manager like systemd or supervisor for uvicorn
5. Set up SSL/TLS certificates
6. Configure CORS properly (restrict origins)
7. Set up daily cron job for `fetch_drops.py`

## EasyPanel Deployment

Bu uygulama EasyPanel'e deploy edilmeye hazırdır. Detaylı talimatlar için `DEPLOY.md` dosyasına bakın.

### Hızlı Başlangıç

1. **Git Repository'ye Push Edin**
   ```bash
   git add .
   git commit -m "Ready for EasyPanel deployment"
   git push
   ```

2. **EasyPanel'de Proje Oluşturun**
   - EasyPanel dashboard'a giriş yapın
   - "New Project" → Git repository URL'inizi girin
   - Build Pack: `Dockerfile` seçin

3. **Environment Variables Ekleyin**
   - `DATABASE_URL`: MySQL bağlantı bilgileri
   - `TRACKED_TLDS`: Takip edilecek TLD'ler (örn: `zip,works,dev,app`)

4. **MySQL Servisi Oluşturun**
   - EasyPanel'de MySQL servisi ekleyin
   - Database: `expireddomain`
   - Character Set: `utf8mb4`

5. **Deploy Edin**
   - "Deploy" butonuna tıklayın
   - Build tamamlandıktan sonra migration'ları çalıştırın:
     ```bash
     alembic upgrade head
     ```

6. **Domain Ayarlayın** (Opsiyonel)
   - Domain ekleyin ve SSL sertifikası alın

Detaylı adımlar için `DEPLOY.md` dosyasına bakın.

## License

This project is for research and monitoring purposes. Ensure compliance with ICANN CZDS terms of service.

## Disclaimer

This service is provided for research and monitoring purposes only. The fact that a domain appears as "dropped" does not guarantee availability for registration. Always verify through official registrars.

