<div align="center">

# 📈 Stock Prices Data Pipeline

**An end-to-end automated data pipeline built with Apache Airflow, Apache Spark, MinIO, PostgreSQL, and Metabase.**

[![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-017CEE?style=for-the-badge&logo=apache-airflow&logoColor=white)](https://airflow.apache.org/)
[![Apache Spark](https://img.shields.io/badge/Apache%20Spark-E25A1C?style=for-the-badge&logo=apache-spark&logoColor=white)](https://spark.apache.org/)
[![MinIO](https://img.shields.io/badge/MinIO-C72E49?style=for-the-badge&logo=minio&logoColor=white)](https://min.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](./LICENSE)

</div>

---

## 📋 Table of Contents

- [📈 Stock Prices Data Pipeline](#-stock-prices-data-pipeline)
  - [📋 Table of Contents](#-table-of-contents)
  - [🔍 Overview](#-overview)
  - [🏗️ Architecture](#️-architecture)
    - [Pipeline Layers](#pipeline-layers)
  - [🛠️ Tech Stack](#️-tech-stack)
  - [📁 Project Structure](#-project-structure)
  - [🚀 Getting Started](#-getting-started)
    - [Prerequisites](#prerequisites)
    - [1. Clone the repository](#1-clone-the-repository)
    - [2. Configure environment variables](#2-configure-environment-variables)
    - [3. Start the full stack](#3-start-the-full-stack)
    - [4. Configure Airflow connections](#4-configure-airflow-connections)
    - [5. Trigger the DAG](#5-trigger-the-dag)
  - [🌐 Services \& Ports](#-services--ports)
  - [⚙️ DAG Tasks](#️-dag-tasks)
  - [🔧 Configuration](#-configuration)
    - [`airflow_settings.yaml`](#airflow_settingsyaml)
    - [`docker-compose.override.yml`](#docker-composeoverrideyml)
    - [`.env` — Native Connection Strings](#env--native-connection-strings)
  - [📚 Documentation](#-documentation)
  - [📄 License](#-license)

---

## 🔍 Overview

This project implements a fully automated **real-time stock price ingestion and analytics pipeline**. It fetches market data from the **Yahoo Finance API**, processes it through **Apache Spark** (via a custom Docker image), stores intermediate and final results in **MinIO** object storage, loads the cleaned data into **PostgreSQL** as a data warehouse, and visualizes insights with **Metabase**. Pipeline completion events are sent as **Slack notifications**.

The entire pipeline is orchestrated by **Apache Airflow** using the modern **TaskFlow API** (`@dag`, `@task`), running inside a multi-container **Docker** environment managed via Astronomer's Astro CLI.

> **New in this version:** The Spark transformation step now runs as a `DockerOperator` using the `airflow/stock-app` custom image. Data loading into PostgreSQL is implemented as a native `@task` using `pandas` + `PostgresHook`, replacing the deprecated Astro SDK approach for full Airflow 3 compatibility.

---

## 🏗️ Architecture

![Pipeline Architecture](./docs/pipeline_architecture.svg)

> The pipeline flows from left to right: data is ingested from Yahoo Finance, processed through Airflow tasks, stored in MinIO, transformed with Spark (inside Docker), loaded into PostgreSQL, and visualized in Metabase. Slack notifications are sent on completion.

```
Yahoo Finance API
      │
      ▼
is_api_available ──► get_stock_prices ──► store_prices ──► format_prices (DockerOperator) ──► get_formatted_csv ──► load_to_dw ──► Slack
                                               │                    │                               │                    │
                                            MinIO               Spark DW                          MinIO            PostgreSQL
                                          (Raw JSON)       (airflow/stock-app)               (Formatted CSV)    (stock_prices table)
                                                                                                                        │
                                                                                                                    Metabase
```

### Pipeline Layers

| Layer | Tasks / Services | Description |
|-------|-----------------|-------------|
| **Ingestion** | `is_api_available`, `get_stock_prices` | HTTP sensor + Yahoo Finance API fetch |
| **Raw Storage** | `store_prices` → MinIO | Store raw JSON in `stock-market/AAPL/` bucket |
| **Processing** | `format_prices` → DockerOperator | Spark job inside `airflow/stock-app` container |
| **Formatted Storage** | `get_formatted_csv` → MinIO | Retrieve cleaned CSV path from `formatted_prices/` |
| **Data Warehouse** | `load_to_dw` → PostgreSQL | Stream CSV from MinIO → `stock_prices` table via pandas |
| **Visualization** | Metabase ← PostgreSQL | BI dashboards and analytics |
| **Notification** | Slack | Pipeline success / failure alerts |

---

## 🛠️ Tech Stack

| Technology | Version | Role |
|------------|---------|------|
| [Apache Airflow](https://airflow.apache.org/) | Astro Runtime `3.1-13` | Pipeline orchestration (Airflow 3) |
| [Yahoo Finance API](https://finance.yahoo.com/) | — | Market data source |
| [MinIO](https://min.io/) | `2024-06-13` | Object storage (raw + formatted data) |
| [Apache Spark](https://spark.apache.org/) | — | Distributed data processing |
| [PostgreSQL](https://www.postgresql.org/) | — | Data warehouse (`stock_prices` table) |
| [Pandas](https://pandas.pydata.org/) | — | CSV → PostgreSQL data loading |
| [Metabase](https://www.metabase.com/) | `v0.52.8.4` | Business intelligence / visualization |
| [Slack](https://slack.com/) | — | Pipeline notifications |
| [Docker](https://www.docker.com/) | — | Containerized runtime environment |

---

## 📁 Project Structure

```
udemy_airflow/
├── dags/                          # Airflow DAG definitions
│   ├── stock_market.py            # Main pipeline DAG (TaskFlow API)
│   ├── taskflow.py                # TaskFlow API example
│   ├── random_number_checker.py   # Sensor + branching example
│   ├── test_load.py               # Debug script for load_to_dw (local dev)
│   └── .airflowignore
├── docs/                          # Project documentation & diagrams
│   ├── pipeline_architecture.svg  # Visual pipeline diagram (SVG)
│   ├── pipeline_architecture.drawio # Editable diagram source
│   └── README.md                  # Documentation index
├── include/                       # Shared project assets
│   ├── stock_market/
│   │   └── tasks.py               # Helper functions: _get_stock_prices,
│   │                              #   _store_prices, _get_formatted_csv
│   ├── helpers/
│   │   └── minio.py               # MinIO client helper
│   └── data/                      # Local volume mounts
│       ├── minio/                 # MinIO data (raw + formatted)
│       └── metabase/              # Metabase persistent data
├── spark/                         # Spark cluster config & custom Docker image
│   ├── master/
│   │   ├── Dockerfile
│   │   └── master.sh
│   ├── worker/
│   │   ├── Dockerfile
│   │   └── worker.sh
│   └── notebooks/                 # Jupyter notebooks for exploration
│       └── stock_transform/
│           └── stock_transform.py # PySpark transformation logic
├── plugins/                       # Custom Airflow plugins
├── tests/                         # DAG integrity and unit tests
├── Dockerfile                     # Astro Runtime image definition
├── docker-compose.override.yml    # Extended services (MinIO, Spark, Metabase, docker-proxy)
├── requirements.txt               # Python dependencies
├── packages.txt                   # OS-level dependencies
├── airflow_settings.yaml          # Local Airflow connections/variables
├── .env                           # Environment variables & native connection strings
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
git clone github.com/Sohila-Khaled-Abbas/udemy_airflow
cd udemy_airflow
```

### 2. Configure environment variables

The `.env` file declares native Airflow connection strings so that **both the scheduler and CLI test commands** automatically pick up all connections without requiring manual UI setup:

```env
# MinIO object storage connection
AIRFLOW_CONN_MINIO=generic://minio:minio123@minio:9000/?endpoint_url=http%3A%2F%2Fminio%3A9000

# PostgreSQL data warehouse connection
AIRFLOW_CONN_POSTGRES=postgresql://postgres:postgres@postgres:5432/postgres
```

> **Note:** The `AIRFLOW_CONN_*` prefix is Airflow's native environment-based connection injection. These are automatically available to all tasks including `astro dev run dags test` without needing the UI.

### 3. Start the full stack

```bash
astro dev start
```

This spins up all containers defined in the `Dockerfile` and `docker-compose.override.yml`:

| Container | Description |
|-----------|-------------|
| `airflow-apiserver` | Airflow UI & REST API (port `8080`) |
| `airflow-scheduler` | DAG scheduling engine |
| `airflow-triggerer` | Deferred task handler |
| `postgres` | Airflow metadata DB + DW (port `5432`) |
| `minio` | Object storage (ports `9000`/`9001`) |
| `spark-master` | Spark master node (port `7077`) |
| `spark-worker` | Spark worker node (port `8081`) |
| `metabase` | BI dashboard (port `3060`) |
| `docker-proxy` | Docker socket proxy (port `2376`) |

> **Port note:** Metabase is mapped to `3060` (not the default `3000`) to avoid conflicts with Windows Hyper-V.

### 4. Configure Airflow connections

Most connections are injected automatically via `.env`. You only need to add the following manually in **Airflow UI → Admin → Connections**:

| Conn ID | Type | Details |
|---------|------|---------|
| `stock_api` | HTTP | Host: `https://query1.finance.yahoo.com`, Extra: `{"endpoint": "/v8/finance/chart/", "headers": {"User-Agent": "..."}}` |
| `slack` | HTTP | Webhook URL from your Slack app |

The `minio` and `postgres` connections are auto-created from `.env` — no manual UI step required.

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

| Task ID | Operator / API | Description |
|---------|----------------|-------------|
| `is_api_available` | `@task.sensor` | Pokes Yahoo Finance API until it returns a valid result |
| `get_stock_prices` | `@task` (Python) | Fetches 1-year daily OHLCV data for `AAPL` |
| `store_prices` | `@task` (Python) | Serializes and uploads raw JSON to MinIO bucket `stock-market/AAPL/` |
| `format_prices` | `DockerOperator` | Runs `airflow/stock-app` image — submits PySpark job via `spark-master` |
| `get_formatted_csv` | `@task` (Python) | Lists `formatted_prices/` in MinIO and returns the output CSV path |
| `load_to_dw` | `@task` (Python) | Downloads CSV from MinIO → loads into PostgreSQL `stock_prices` table via `pandas` + `PostgresHook` |

> **Implementation note:** `load_to_dw` uses a native Airflow `@task` with `pandas` and `PostgresHook` rather than the Astro SDK (`aql.load_file`). This ensures full compatibility with **Airflow 3** (Astro Runtime 3.1-13), which removed the `airflow.hooks.dbapi` module that `astro-sdk-python` depended on.

---

## 🔧 Configuration

### `airflow_settings.yaml`

Used for **local development only**. Defines Airflow connections, variables, and pools without using the UI. See [Astronomer docs](https://www.astronomer.io/docs/astro/cli/develop-project#configure-airflow_settingsyaml-local-development-only).

### `docker-compose.override.yml`

Extends the default Astro `docker-compose.yml` to add:
- **MinIO** — object storage on ports `9000` (API) / `9001` (Console)
- **Spark** master + worker on ports `7077`, `8081`, `8082`
- **Metabase** BI tool on port `3060` (remapped from default `3000` to avoid Windows Hyper-V conflicts)
- **docker-proxy** — exposes Docker socket safely on port `2376`

All services share the `ndsnet` bridge network.

### `.env` — Native Connection Strings

Airflow 3 supports injecting connections via environment variables using the `AIRFLOW_CONN_<CONN_ID>` pattern. This is particularly important for `astro dev run dags test`, which runs in an isolated CLI container that **cannot access connections created via the Airflow UI**.

```env
AIRFLOW_CONN_MINIO=generic://minio:minio123@minio:9000/?endpoint_url=http%3A%2F%2Fminio%3A9000
AIRFLOW_CONN_POSTGRES=postgresql://postgres:postgres@postgres:5432/postgres
```

### `requirements.txt`

| Package | Purpose |
|---------|---------|
| `apache-airflow-providers-http` | Yahoo Finance HTTP sensor |
| `apache-airflow-providers-amazon` | S3/MinIO compat layer |
| `minio==7.2.14` | MinIO Python SDK |
| `apache-airflow-providers-docker==4.0.0` | `DockerOperator` for Spark |
| `apache-airflow-providers-postgres` | `PostgresHook` for data loading |
| `astro-sdk-python` | (installed but unused; native `@task` preferred for Airflow 3 compat) |

---

## 📚 Documentation

Full architectural documentation is in the [`docs/`](./docs/README.md) folder:

| File | Description |
|------|-------------|
| [`docs/README.md`](./docs/README.md) | Documentation index and diagram guide |
| [`docs/pipeline_architecture.svg`](./docs/pipeline_architecture.svg) | Modernized SVG pipeline diagram |
| [`docs/pipeline_architecture.drawio`](./docs/pipeline_architecture.drawio) | Editable draw.io source |

---

## 📄 License

This project is licensed under the **MIT License** — see [`LICENSE`](./LICENSE) for details.

---

<div align="center">
  <sub>Built with ❤️ using Apache Airflow, Spark, MinIO, PostgreSQL &amp; Metabase</sub>
</div>
