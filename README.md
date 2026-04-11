<div align="center">

# 📈 Stock Prices Data Pipeline

**An end-to-end automated data pipeline built with Apache Airflow, Apache Spark, MinIO, PostgreSQL, and Metabase.**

[![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-017CEE?style=for-the-badge&logo=apache-airflow&logoColor=white)](https://airflow.apache.org/)
[![Apache Spark](https://img.shields.io/badge/Apache%20Spark-E25A1C?style=for-the-badge&logo=apache-spark&logoColor=white)](https://spark.apache.org/)
[![MinIO](https://img.shields.io/badge/MinIO-C72E49?style=for-the-badge&logo=minio&logoColor=white)](https://min.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Slack](https://img.shields.io/badge/Slack-4A154B?style=for-the-badge&logo=slack&logoColor=white)](https://slack.com/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](./LICENSE)

</div>

---

## 📋 Table of Contents

- [🔍 Overview](#-overview)
- [🏗️ Architecture](#️-architecture)
- [🛠️ Tech Stack](#️-tech-stack)
- [📁 Project Structure](#-project-structure)
- [🚀 Getting Started](#-getting-started)
- [🌐 Services & Ports](#-services--ports)
- [⚙️ DAG Tasks](#️-dag-tasks)
- [🔧 Configuration](#-configuration)
- [📚 Documentation](#-documentation)
- [📊 Stock Dashboard](#-stock-dashboard)
- [📄 License](#-license)

---

## 🔍 Overview

This project implements a fully automated **real-time stock price ingestion and analytics pipeline**. It fetches market data from the **Yahoo Finance API**, processes it through **Apache Spark** (via a custom Docker image), stores intermediate and final results in **MinIO** object storage, loads the cleaned data into **PostgreSQL** as a data warehouse, and visualizes insights with **Metabase**. Pipeline completion events are sent as **Slack notifications** using `SlackNotifier`.

The entire pipeline is orchestrated by **Apache Airflow** using the modern **TaskFlow API** (`@dag`, `@task`), running inside a multi-container **Docker** environment managed via Astronomer's Astro CLI.

> **Architecture highlights:**
> - Spark transformation runs as a `DockerOperator` using a custom `airflow/stock-app` image
> - PostgreSQL loading uses a native `@task` with `pandas` + `PostgresHook` (Airflow 3 compatible)
> - Slack alerts use `SlackNotifier` from `airflow.providers.slack.notifications.slack` (provider v9.9.0)
> - Connections are injected via `.env` native `AIRFLOW_CONN_*` variables — no UI setup required

---

## 🏗️ Architecture

![Pipeline Architecture](./docs/pipeline_architecture.svg)

> The pipeline flows left to right: data ingested from Yahoo Finance → stored raw in MinIO → transformed with Spark (DockerOperator) → formatted CSV stored back in MinIO → loaded into PostgreSQL → visualized in Metabase. Slack notifications fire on DAG success or failure.

```
Yahoo Finance API
      │
      ▼
is_api_available ──► get_stock_prices ──► store_prices ──► format_prices ──► get_formatted_csv ──► load_to_dw
                                               │            (DockerOperator)          │                   │
                                           MinIO /               Spark            MinIO /           PostgreSQL
                                        stock-market/AAPL/    airflow/stock-app  formatted_prices/  stock_prices
                                          (Raw JSON)                               (CSV)                 │
                                                                                                     Metabase
                                                                                   ◄── SlackNotifier (success/failure) ───┘
```

### Pipeline Layers

| Layer | Tasks / Services | Description |
|-------|-----------------|-------------|
| **Ingestion** | `is_api_available`, `get_stock_prices` | HTTP sensor + Yahoo Finance API fetch |
| **Raw Storage** | `store_prices` → MinIO | Upload raw JSON to `stock-market/AAPL/prices.json` |
| **Processing** | `format_prices` → `DockerOperator` | Spark job inside `airflow/stock-app` container via `spark-master` |
| **Formatted Storage** | `get_formatted_csv` → MinIO | Retrieve cleaned CSV path from `AAPL/formatted_prices/` |
| **Data Warehouse** | `load_to_dw` → PostgreSQL | Stream CSV from MinIO → `public.stock_prices` via pandas |
| **Visualization** | Metabase ← PostgreSQL | BI dashboards on historical AAPL data |
| **Notification** | `SlackNotifier` | DAG-level success / failure alerts to `#general` |

---

## 🛠️ Tech Stack

| Technology | Version | Role |
|------------|---------|------|
| [Apache Airflow](https://airflow.apache.org/) | Astro Runtime `3.1-13` | Pipeline orchestration (Airflow 3, TaskFlow API) |
| [Yahoo Finance API](https://finance.yahoo.com/) | — | Market data source (`/v8/finance/chart/`) |
| [MinIO](https://min.io/) | `RELEASE.2024-06-13` | Object storage — raw JSON + formatted CSV |
| [Apache Spark](https://spark.apache.org/) | Custom image | Distributed data transformation |
| [PostgreSQL](https://www.postgresql.org/) | — | Data warehouse (`public.stock_prices` table) |
| [Pandas](https://pandas.pydata.org/) | — | CSV → PostgreSQL loading via `PostgresHook` |
| [Metabase](https://www.metabase.com/) | `v0.52.8.4` | Business intelligence / visualization |
| [Slack](https://slack.com/) | Provider `9.9.0` | DAG success/failure notifications (`SlackNotifier`) |
| [Docker](https://www.docker.com/) | — | Containerized runtime environment |

---

## 📁 Project Structure

```
udemy_airflow/
├── dags/                              # Airflow DAG definitions
│   ├── stock_market.py                # Main pipeline DAG (TaskFlow API + SlackNotifier)
│   ├── taskflow.py                    # TaskFlow API example DAG
│   ├── random_number_checker.py       # Sensor + branching example DAG
│   ├── test_load.py                   # Debug script for load_to_dw (local dev)
│   └── .airflowignore
├── docs/                              # Project documentation & diagrams
│   ├── pipeline_architecture.svg      # Modernized SVG pipeline diagram
│   ├── pipeline_architecture.drawio   # Editable draw.io source
│   ├── pipeline_architecture.png      # PNG export for embeds
│   ├── stock_market-graph.png         # Airflow DAG graph screenshot
│   ├── Stock Dashboard.pdf            # Metabase dashboard export (PDF)
│   └── README.md                      # Documentation index
├── include/                           # Shared project assets
│   ├── stock_market/
│   │   └── tasks.py                   # Helper functions:
│   │                                  #   _get_stock_prices  — fetch OHLCV from Yahoo Finance
│   │                                  #   _store_prices      — upload raw JSON to MinIO
│   │                                  #   _get_formatted_csv — retrieve Spark output CSV path
│   ├── helpers/
│   │   └── minio.py                   # MinIO client helper utilities
│   └── data/                          # Local Docker volume mounts
│       ├── minio/                     # MinIO persistent data
│       └── metabase/                  # Metabase persistent data
├── spark/                             # Custom Spark Docker images
│   ├── master/
│   │   ├── Dockerfile                 # Spark master image
│   │   └── master.sh
│   ├── worker/
│   │   ├── Dockerfile                 # Spark worker image
│   │   └── worker.sh
│   └── notebooks/
│       └── stock_transform/
│           └── stock_transform.py     # PySpark transformation logic
├── plugins/                           # Custom Airflow plugins
├── tests/                             # DAG integrity and unit tests
├── Dockerfile                         # Astro Runtime base image (astrocrpublic.azurecr.io/runtime:3.1-13)
├── docker-compose.override.yml        # Extended services (MinIO, Spark, Metabase, docker-proxy)
├── requirements.txt                   # Python dependencies
├── packages.txt                       # OS-level dependencies
├── airflow_settings.yaml              # Local Airflow connections/variables (dev only)
├── .env                               # Native AIRFLOW_CONN_* connection strings
├── .gitignore
└── LICENSE
```

---

## 🚀 Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
- [Astronomer CLI](https://www.astronomer.io/docs/astro/cli/install-cli) (`astro`)

### 1. Clone the repository

```bash
git clone https://github.com/Sohila-Khaled-Abbas/udemy_airflow
cd udemy_airflow
```

### 2. Configure environment variables

The `.env` file injects Airflow connections using the `AIRFLOW_CONN_*` native pattern, so **both the scheduler and `astro dev run` CLI** pick them up automatically — no UI setup required:

```env
# MinIO object storage
AIRFLOW_CONN_MINIO=generic://minio:minio123@minio:9000/?endpoint_url=http%3A%2F%2Fminio%3A9000

# PostgreSQL data warehouse
AIRFLOW_CONN_POSTGRES=postgresql://postgres:postgres@postgres:5432/postgres
```

### 3. Build the Spark images and start the stack

```bash
# Build custom Spark images first
docker build -t airflow/spark-master ./spark/master
docker build -t airflow/spark-worker ./spark/worker

# Start all services
astro dev start
```

This spins up all containers defined in `Dockerfile` and `docker-compose.override.yml`:

| Container | Description |
|-----------|-------------|
| `airflow-apiserver` | Airflow UI & REST API (port `8080`) |
| `airflow-scheduler` | DAG scheduling engine |
| `airflow-triggerer` | Deferred task handler |
| `postgres` | Airflow metadata DB + DW (port `5432`) |
| `minio` | Object storage (ports `9000` / `9001`) |
| `spark-master` | Spark master node (port `7077`, UI `8082`) |
| `spark-worker` | Spark worker node (UI `8081`) |
| `metabase` | BI dashboard (port `3060`) |
| `docker-proxy` | Docker socket proxy (port `2376`) |

> **Port note:** Metabase is mapped to `3060` (not default `3000`) to avoid conflicts with Windows Hyper-V.

### 4. Configure Airflow connections

The `minio` and `postgres` connections are auto-loaded from `.env`. You only need to add the following manually via **Airflow UI → Admin → Connections**:

| Conn ID | Type | Details |
|---------|------|---------|
| `stock_api` | HTTP | Host: `https://query1.finance.yahoo.com`<br>Extra: `{"endpoint": "/v8/finance/chart/", "headers": {"User-Agent": "Mozilla/5.0"}}` |
| `slack` | HTTP | Password: your Slack Incoming Webhook URL |

### 5. Trigger the DAG

Navigate to [http://localhost:8080](http://localhost:8080) → enable and trigger the `stock_market` DAG.

Or test from the CLI:

```bash
astro dev run dags test stock_market 2025-01-06
```

---

## 🌐 Services & Ports

| Service | URL | Credentials |
|---------|-----|-------------|
| Airflow UI | [http://localhost:8080](http://localhost:8080) | `admin` / `admin` |
| MinIO Console | [http://localhost:9001](http://localhost:9001) | `minio` / `minio123` |
| Spark Master UI | [http://localhost:8082](http://localhost:8082) | — |
| Spark Worker UI | [http://localhost:8081](http://localhost:8081) | — |
| Metabase | [http://localhost:3060](http://localhost:3060) | Set on first launch |
| PostgreSQL | `localhost:5432` | `postgres` / `postgres` |

---

## ⚙️ DAG Tasks

![DAG Graph](./docs/stock_market-graph.png)
*↑ Airflow DAG showing the complete pipeline execution — from API sensor through to `load_to_dw`*

| Task ID | Operator / API | Description |
|---------|----------------|-------------|
| `is_api_available` | `@task.sensor` | Pokes Yahoo Finance every 30s until the API returns a valid result |
| `get_stock_prices` | `@task` | Fetches 1-year daily OHLCV data for `AAPL` from Yahoo Finance |
| `store_prices` | `@task` | Serializes response and uploads raw JSON to MinIO `stock-market/AAPL/prices.json` |
| `format_prices` | `DockerOperator` | Runs `airflow/stock-app` image — submits PySpark job via `spark-master` (network: `container:spark-master`) |
| `get_formatted_csv` | `@task` | Lists `AAPL/formatted_prices/` in MinIO, returns the output `.csv` path |
| `load_to_dw` | `@task` | Downloads CSV from MinIO → loads into PostgreSQL `public.stock_prices` table via `pandas` + `PostgresHook` |

**DAG-level callbacks:**

| Event | Handler | Details |
|-------|---------|---------|
| `on_success_callback` | `SlackNotifier` | Posts "Stock market DAG succeeded" to `#general` |
| `on_failure_callback` | `SlackNotifier` | Posts "Stock market DAG failed" to `#general` |

> **Note:** `SlackNotifier` is imported from `airflow.providers.slack.notifications.slack` (the correct module path for provider `v9.9.0`). The class lives in `slack.py`, not `slack_notifier.py`.

---

## 🔧 Configuration

### `Dockerfile`

```dockerfile
FROM astrocrpublic.azurecr.io/runtime:3.1-13
```

Uses Astronomer's Astro Runtime `3.1-13` (based on Airflow 3) as the base image. All pip dependencies are installed via `requirements.txt`.

### `requirements.txt`

| Package | Purpose |
|---------|---------|
| `apache-airflow-providers-http` | Yahoo Finance HTTP sensor |
| `apache-airflow-providers-amazon` | S3/MinIO compatibility layer |
| `minio==7.2.14` | MinIO Python SDK |
| `apache-airflow-providers-docker==4.0.0` | `DockerOperator` for Spark |
| `apache-airflow-providers-postgres` | `PostgresHook` for data loading |
| `apache-airflow-providers-slack==9.9.0` | `SlackNotifier` for pipeline alerts |
| `astro-sdk-python` | Installed but unused — native `@task` preferred for Airflow 3 compat |

### `docker-compose.override.yml`

Extends the default Astro compose file to add:
- **MinIO** — object storage on ports `9000` (S3 API) / `9001` (Console)
- **Spark** master + worker — ports `7077`, `8082` (master UI), `8081` (worker UI)
- **Metabase** — BI tool on port `3060` (remapped from `3000` to avoid Windows Hyper-V conflicts)
- **docker-proxy** — exposes Docker socket safely on port `2376` via `alpine/socat`

All services share the `ndsnet` bridge network.

### `airflow_settings.yaml`

Used for **local development only**. Defines Airflow connections, variables, and pools without using the UI. See [Astronomer docs](https://www.astronomer.io/docs/astro/cli/develop-project#configure-airflow_settingsyaml-local-development-only).

### `.env` — Native Connection Strings

Airflow 3 supports injecting connections via `AIRFLOW_CONN_<CONN_ID>` environment variables. This is critical for `astro dev run dags test`, which runs in an isolated CLI container that **cannot access UI-created connections**:

```env
AIRFLOW_CONN_MINIO=generic://minio:minio123@minio:9000/?endpoint_url=http%3A%2F%2Fminio%3A9000
AIRFLOW_CONN_POSTGRES=postgresql://postgres:postgres@postgres:5432/postgres
```

---

## 📚 Documentation

Full architectural documentation lives in the [`docs/`](./docs/README.md) folder:

| File | Description |
|------|-------------|
| [`docs/README.md`](./docs/README.md) | Documentation index and diagram guide |
| [`docs/pipeline_architecture.svg`](./docs/pipeline_architecture.svg) | Modernized SVG pipeline architecture diagram |
| [`docs/pipeline_architecture.drawio`](./docs/pipeline_architecture.drawio) | Editable draw.io source file |
| [`docs/pipeline_architecture.png`](./docs/pipeline_architecture.png) | PNG export of architecture diagram |
| [`docs/stock_market-graph.png`](./docs/stock_market-graph.png) | Airflow UI DAG graph screenshot |
| [`docs/Stock Dashboard.pdf`](./docs/Stock%20Dashboard.pdf) | Metabase dashboard export (PDF) |

---

## 📊 Stock Dashboard

<div align="center">

[![Download Dashboard PDF](https://img.shields.io/badge/📄%20Download-Stock%20Dashboard%20PDF-C72E49?style=for-the-badge)](./docs/Stock%20Dashboard.pdf)

</div>

The **Stock Dashboard** was created in [Metabase](http://localhost:3060) connected to the `public.stock_prices` PostgreSQL table populated by the pipeline. It provides an at-a-glance view of historical AAPL stock data after Spark transformation.

> **📄 View the full Metabase dashboard export:** [`docs/Stock Dashboard.pdf`](./docs/Stock%20Dashboard.pdf)

To rebuild the dashboard in your local Metabase instance:

1. Navigate to [http://localhost:3060](http://localhost:3060) and complete the initial setup
2. Add a **PostgreSQL** data source:
   - Host: `postgres`, Port: `5432`
   - Database: `postgres`, User: `postgres`, Password: `postgres`
3. Browse to the `public` schema → `stock_prices` table
4. Build questions and dashboards from the loaded AAPL data

---

## 📄 License

This project is licensed under the **MIT License** — see [`LICENSE`](./LICENSE) for details.

---

<div align="center">
  <sub>Built with ❤️ using Apache Airflow, Spark, MinIO, PostgreSQL, Metabase &amp; Slack</sub>
</div>
