# Multi-source News Crawler

Project Python 3.11+ de crawl tin tuc tu 4 nguon:

- `https://vnexpress.net`
- `https://cafef.vn`
- `https://genk.vn`
- `https://diendandoanhnghiep.vn`

He thong duoc thiet ke theo huong production-friendly:

- crawl da nguon
- crawl tu homepage + nhieu category + pagination
- luu raw page va article da chuan hoa
- dedup theo `url_hash` va `content_hash`
- luu lich su crawl tung lan chay va tong hop theo ngay
- de migrate len cloud / Databricks sau nay

## 1. Cau truc project

```text
.
|-- app
|   |-- __init__.py
|   |-- main.py
|   |-- config.py
|   |-- ai
|   |   |-- __init__.py
|   |   |-- service.py
|   |   |-- summarizer.py
|   |   `-- types.py
|   |-- analytics
|   |   |-- __init__.py
|   |   |-- repository.py
|   |   `-- service.py
|   |-- db
|   |   |-- __init__.py
|   |   |-- base.py
|   |   |-- session.py
|   |   `-- models.py
|   |-- ingestion
|   |   |-- __init__.py
|   |   |-- contracts.py
|   |   |-- service.py
|   |   |-- crawlers
|   |   |   |-- __init__.py
|   |   |   |-- base_crawler.py
|   |   |   |-- vnexpress_crawler.py
|   |   |   |-- cafef_crawler.py
|   |   |   |-- genk_crawler.py
|   |   |   `-- diendandoanhnghiep_crawler.py
|   |   |-- dedup
|   |   |   |-- __init__.py
|   |   |   `-- service.py
|   |   `-- parsers
|   |       |-- __init__.py
|   |       `-- common.py
|   |-- repositories
|   |   |-- __init__.py
|   |   |-- article_repository.py
|   |   |-- crawl_job_repository.py
|   |   `-- raw_page_repository.py
|   |-- scheduler
|   |   |-- __init__.py
|   |   `-- service.py
|   |-- services
|   |   |-- __init__.py
|   |   `-- crawl_service.py
|   `-- utils
|       |-- __init__.py
|       |-- logger.py
|       `-- helpers.py
|-- migrations
|   |-- env.py
|   |-- script.py.mako
|   `-- versions
|-- tests
|   `-- test_vnexpress_parser.py
|-- .env.example
|-- alembic.ini
|-- docker-compose.yml
|-- Dockerfile
|-- README.md
`-- requirements.txt
```

## 2. Kien truc chinh

- `app/ingestion/crawlers/*`: implementation crawler theo tung site, xu ly HTTP client, retry, delay, normalize links, category pages, pagination.
- `app/ingestion/parsers/common.py`: parser/helper dung chung cho crawler.
- `IngestionService`: fetch + extract links + parse + dedup selection truoc khi persist.
- `CrawlService`: orchestration runtime, tao `crawl_jobs`, persist qua repository layer, cap nhat `crawl_daily_summaries`.
- `app/repositories/*`: data access layer cho `sources`, `raw_pages`, `articles`, `crawl_jobs`.
- `SchedulerService`: chay ingestion theo lich APScheduler.
- `Alembic`: quan ly schema migration.

## 3. Database tables

Schema hien tai co cac bang chinh:

- `sources`
- `crawl_jobs`
- `crawl_daily_summaries`
- `raw_pages`
- `articles`
- `categories`
- `article_categories`
- `authors`
- `article_authors`

Y nghia:

- `crawl_jobs`: lich su tung lan chay crawl
- `crawl_daily_summaries`: tong hop ket qua theo tung ngay va tung source
- `raw_pages`: luu raw HTML va text sau khi fetch
- `articles`: du lieu bai viet da parse va chuan hoa

## 4. Crawler strategy hien tai

Crawler khong chi lay link tu homepage nua.

Moi source hien tai:

- co danh sach category hardcode trong crawler
- tao URL pagination rieng cho tung site
- crawl `homepage + category pages`
- mac dinh crawl `10` trang cho moi category
- loc link bai viet bang regex rieng
- dedup link bang `url_hash`

Pipeline hien tai:

1. `fetch`
2. `extract links`
3. `parse article`
4. `dedup selection`
5. `persist raw page`
6. `persist article`

## 5. Yeu cau moi truong

- Python `3.11+`
- PostgreSQL
- Docker + Docker Compose neu muon chay bang container

## 6. Cau hinh `.env`

Tao file `.env` tu file mau:

```cmd
copy .env.example .env
```

Gia tri mau:

```env
APP_NAME=multi-source-news-crawler
APP_ENV=local
LOG_LEVEL=INFO
APP_TIMEZONE=Asia/Ho_Chi_Minh
POSTGRES_DB=news_crawler
POSTGRES_USER=postgres
POSTGRES_PASSWORD=1307
DATABASE_URL=postgresql+psycopg://postgres:1307@localhost:5432/news_crawler
SCHEDULER_HOUR=7
SCHEDULER_MINUTE=0
CRAWL_TIMEOUT_SECONDS=20
CRAWL_RETRY_COUNT=3
CRAWL_REQUEST_DELAY_SECONDS=0.3
CRAWL_CATEGORY_PAGES=10
PARSER_VERSION=1.0.0
ARTICLE_STATUS_DEFAULT=published
SAVE_RAW_HTML=true
ENABLED_SOURCES=vnexpress,cafef,genk,diendandoanhnghiep
```

Neu chay bang Docker, doi `DATABASE_URL` thanh:

```env
DATABASE_URL=postgresql+psycopg://postgres:1307@postgres:5432/news_crawler
```

## 7. Chay thu nhanh

Neu ban muon kiem tra he thong co chay duoc hay khong, day la luong toi thieu de test local:

### 7.1. Chuan bi moi truong

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

### 7.2. Tao database va schema

Tao database `news_crawler` trong PostgreSQL, sau do chay:

```cmd
alembic upgrade head
```

### 7.3. Chay test parser

```cmd
python -m pytest
```

### 7.4. Crawl thu 1 nguon

```cmd
python -m app.main crawl_source --source vnexpress
```

Neu thanh cong, log se hien thi tong so bai tim thay, so bai insert duoc va so bai loi.

### 7.5. Crawl tat ca nguon

```cmd
python -m app.main crawl_all
```

### 7.6. Chay scheduler

```cmd
python -m app.main run_scheduler
```

Mac dinh scheduler chay luc `07:00` moi ngay theo `APP_TIMEZONE`.

## 8. Chay local bang virtualenv

### 8.1. Tao virtualenv

```cmd
python -m venv .venv
.venv\Scripts\activate
```

### 8.2. Cai dependencies

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

### 8.3. Tao database `news_crawler`

Loi ban gap truoc do la:

```text
FATAL: database "news_crawler" does not exist
```

Nen ban phai tao DB truoc khi chay Alembic.

Neu da co `psql` trong PATH:

```cmd
psql -U postgres -h localhost -p 5432 -d postgres
```

Nhap password, sau do trong `psql` chay:

```sql
CREATE DATABASE news_crawler;
\q
```

Neu khong co `psql` trong PATH, ban co the tao DB bang pgAdmin.

### 8.4. Chay migration

```cmd
alembic upgrade head
```

### 8.5. Chay test

```cmd
python -m pytest
```

### 8.6. Crawl thu 1 source

```cmd
python -m app.main crawl_source --source vnexpress
python -m app.main crawl_source --source cafef
python -m app.main crawl_source --source genk
python -m app.main crawl_source --source diendandoanhnghiep
```

Ban co the thay `vnexpress` bang:

- `cafef`
- `genk`
- `diendandoanhnghiep`

### 8.7. Crawl tat ca source

```cmd
python -m app.main crawl_all
```

### 8.8. Chay scheduler hang ngay

```cmd
python -m app.main run_scheduler
```

Mac dinh scheduler chay luc `07:00` moi ngay theo `APP_TIMEZONE`.

## 9. Chay bang Docker

### 9.1. Tao `.env`

```cmd
copy .env.example .env
```

Sua lai toi thieu:

```env
POSTGRES_PASSWORD=1307
DATABASE_URL=postgresql+psycopg://postgres:1307@postgres:5432/news_crawler
```

### 9.2. Khoi dong PostgreSQL

```cmd
docker compose up -d postgres
```

### 9.3. Tao schema

```cmd
docker compose run --rm app alembic upgrade head
```

### 9.4. Crawl thu trong container

```cmd
docker compose run --rm app python -m app.main crawl_source --source vnexpress
```

### 9.5. Crawl tat ca trong container

```cmd
docker compose run --rm app python -m app.main crawl_all
```

### 9.6. Chay scheduler trong container

```cmd
docker compose up -d --build app
docker compose logs -f app
```

### 9.7. Dung container

```cmd
docker compose down
```

Neu muon xoa ca volume database:

```cmd
docker compose down -v
```

## 10. Thu tu chay de project hoat dong

### Cach 1: Local

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
psql -U postgres -h localhost -p 5432 -d postgres
```

Trong `psql`:

```sql
CREATE DATABASE news_crawler;
\q
```

Quay lai `cmd`:

```cmd
alembic upgrade head
python -m pytest
python -m app.main crawl_source --source vnexpress
python -m app.main crawl_all
python -m app.main run_scheduler
```

### Cach 2: Docker

```cmd
copy .env.example .env
```

Sua `.env`:

```env
POSTGRES_PASSWORD=1307
DATABASE_URL=postgresql+psycopg://postgres:1307@postgres:5432/news_crawler
```

Sau do:

```cmd
docker compose up -d postgres
docker compose run --rm app alembic upgrade head
docker compose run --rm app python -m pytest
docker compose run --rm app python -m app.main crawl_source --source vnexpress
docker compose run --rm app python -m app.main crawl_all
docker compose up -d --build app
docker compose logs -f app
```

## 11. Cac lenh CLI

### Crawl tat ca source

```cmd
python -m app.main crawl_all
```

### Crawl 1 source

```cmd
python -m app.main crawl_source --source vnexpress
```

### Chay scheduler

```cmd
python -m app.main run_scheduler
```

## 12. Config crawler quan trong

Ban co the dieu chinh trong `.env`:

- `CRAWL_CATEGORY_PAGES=10`
  - so trang moi category se crawl
- `CRAWL_REQUEST_DELAY_SECONDS=0.3`
  - delay giua cac request de giam nguy co bi block
- `CRAWL_RETRY_COUNT=3`
  - so lan retry khi request fail
- `CRAWL_TIMEOUT_SECONDS=20`
  - timeout cho moi request

## 13. Lich su crawl theo ngay nam o dau

Phan luu lich su crawl theo ngay hien tai nam o:

- `app/db/models.py`
  - class `CrawlDailySummary`
- `app/services/crawl_service.py`
  - `_start_daily_summary(...)`
  - `_finish_daily_summary(...)`
- `migrations/versions/20260410_0002_add_crawl_daily_summaries.py`

## 14. Mo rong sau nay

- them sitemap crawling cho tung site
- them stop condition khi page pagination khong con bai moi
- them metrics theo category
- day raw data len object storage / Delta Lake
- full-text search bang PostgreSQL `tsvector` hoac OpenSearch
