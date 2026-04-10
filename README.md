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
  - [📚 Documentation](#-documentation)
  - [📄 License](#-license)

---

## 🔍 Overview

This project implements a fully automated **real-time stock price ingestion and analytics pipeline**. It fetches market data from the **Yahoo Finance API**, processes it through **Apache Spark**, stores intermediate and final results in **MinIO** object storage, loads the cleaned data into **PostgreSQL** as a data warehouse, and visualizes insights with **Metabase**. Pipeline completion events are sent as **Slack notifications**.

The entire pipeline is orchestrated by **Apache Airflow** using the modern **TaskFlow API** (`@dag`, `@task`), running inside a multi-container **Docker** environment managed via Astronomer's Astro CLI.

---

## 🏗️ Architecture

![Pipeline Architecture](./docs/pipeline_architecture.svg)

> The pipeline flows from left to right: data is ingested from Yahoo Finance, processed through Airflow tasks, stored in MinIO, transformed with Spark, loaded into PostgreSQL, and visualized in Metabase. Slack notifications are sent on completion.

```
Yahoo Finance API
      │
      ▼
is_api_available ──► get_stock_prices   ──► store_prices ──► format_prices ──► get_formatted_csv ──► load_to_dw ──► Slack
                                                 │                  │                   │                   │
                                              MinIO              Spark               MinIO            PostgreSQL
                                           (Raw Data)         (Transform)         (Formatted)        (DW / BI)
                                                                                                          │
                                                                                                       Metabase
```

### Pipeline Layers

| Layer | Tasks / Services | Description |
|-------|-----------------|-------------|
| **Ingestion** | `is_api_available`, `get_stock_prices` | HTTP sensor + Yahoo Finance API fetch |
| **Raw Storage** | `store_prices` → MinIO | Store raw JSON/CSV in object storage |
| **Processing** | `format_prices` → Apache Spark | Distributed transformation and formatting |
| **Formatted Storage** | `get_formatted_csv` → MinIO | Store cleaned CSV for downstream use |
| **Data Warehouse** | `load_to_dw` → PostgreSQL | Bulk load formatted data into the DW |
| **Visualization** | Metabase ← PostgreSQL | BI dashboards and analytics |
| **Notification** | `load_to_dw` → Slack | Pipeline success / failure alerts |

---

## 🛠️ Tech Stack

| Technology | Version | Role |
|------------|---------|------|
| [Apache Airflow](https://airflow.apache.org/) | Astro Runtime 3.1-13 | Pipeline orchestration |
| [Yahoo Finance API](https://finance.yahoo.com/) | — | Market data source |
| [MinIO](https://min.io/) | `2024-06-13` | Object storage (raw + formatted data) |
| [Apache Spark](https://spark.apache.org/) | — | Distributed data processing |
| [PostgreSQL](https://www.postgresql.org/) | — | Data warehouse |
| [Metabase](https://www.metabase.com/) | `v0.52.8.4` | Business intelligence / visualization |
| [Slack](https://slack.com/) | — | Pipeline notifications |
| [Docker](https://www.docker.com/) | — | Containerized runtime environment |

---

## 📁 Project Structure

```
udemy_airflow/
├── dags/                          # Airflow DAG definitions
│   └── .airflowignore
├── docs/                          # Project documentation & diagrams
│   ├── pipeline_architecture.svg  # Visual pipeline diagram (SVG)
│   ├── pipeline_architecture.drawio # Editable diagram source
│   └── README.md                  # Documentation index
├── include/                       # Shared project assets
│   ├── helpers/
│   │   └── minio.py               # MinIO client helper
│   └── data/                      # Local volume mounts
│       ├── minio/                 # MinIO data (raw + formatted)
│       └── metabase/              # Metabase persistent data
├── spark/                         # Spark cluster config
│   ├── master/
│   │   ├── Dockerfile
│   │   └── master.sh
│   ├── worker/
│   │   ├── Dockerfile
│   │   └── worker.sh
│   └── notebooks/                 # Jupyter notebooks for exploration
├── plugins/                       # Custom Airflow plugins
├── tests/                         # DAG and unit tests
├── Dockerfile                     # Astro Runtime image
├── docker-compose.override.yml    # Extended services (MinIO, Spark, Metabase)
├── requirements.txt               # Python dependencies
├── packages.txt                   # OS-level dependencies
├── airflow_settings.yaml          # Local Airflow connections/variables
├── .env                           # Environment variables (not committed)
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

Copy and fill in the required values:

```bash
cp .env.example .env   # edit with your credentials
```

Key variables to set:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
MINIO_ROOT_USER=minio
MINIO_ROOT_PASSWORD=minio123
```

### 3. Start the full stack

```bash
astro dev start
```

This spins up all containers defined in the `Dockerfile` and `docker-compose.override.yml`:

| Container | Description |
|-----------|-------------|
| `airflow-apiserver` | Airflow UI & REST API |
| `airflow-scheduler` | DAG scheduling engine |
| `airflow-triggerer` | Deferred task handler |
| `postgres` | Airflow metadata DB |
| `minio` | Object storage |
| `spark-master` | Spark master node |
| `spark-worker` | Spark worker node |
| `metabase` | BI dashboard |
| `docker-proxy` | Docker socket proxy |

### 4. Configure Airflow connections

Go to **Airflow UI → Admin → Connections** and add:

| Conn ID | Type | Details |
|---------|------|---------|
| `aws_default` | Amazon S3 | Endpoint: `http://minio:9000`, Key/Secret from `.env` |
| `minio` | Generic | Endpoint: `http://minio:9000`, Login: `minio`, Pass: `minio123` |
| `stock_api` | HTTP | Host: `https://query1.finance.yahoo.com` |
| `spark_default` | Spark | Master: `spark://spark-master:7077` |
| `slack` | HTTP | Webhook URL from `.env` |
| `postgres_default` | Postgres | Host: `postgres`, DB: `postgres` |

### 5. Trigger the DAG

Navigate to [http://localhost:8080](http://localhost:8080) → enable and trigger your stock prices DAG.

---

## 🌐 Services & Ports

| Service | URL | Credentials |
|---------|-----|-------------|
| Airflow UI | [http://localhost:8080](http://localhost:8080) | `admin` / `admin` |
| MinIO Console | [http://localhost:9001](http://localhost:9001) | `minio` / `minio123` |
| Spark Master UI | [http://localhost:8082](http://localhost:8082) | — |
| Spark Worker UI | [http://localhost:8081](http://localhost:8081) | — |
| Metabase | [http://localhost:3000](http://localhost:3000) | Set on first launch |
| PostgreSQL | `localhost:5432` | `postgres` / `postgres` |

---

## ⚙️ DAG Tasks

| Task ID | Operator / API | Description |
|---------|----------------|-------------|
| `is_api_available` | `@task.sensor` | Checks Yahoo Finance API availability |
| `get_stock_prices` | `@task` (Python) | Fetches current stock prices using requests |
| `store_prices` | `@task` (Python) | Uploads raw data to MinIO with dynamic fallback |
| `format_prices` | `SparkSubmitOperator` | Runs Spark job to clean and format data |
| `get_formatted_csv` | `PythonOperator` | Downloads formatted CSV from MinIO |
| `load_to_dw` | `PythonOperator` | Inserts data into PostgreSQL |
| `notify_slack` | `SlackWebhookOperator` | Sends pipeline summary to Slack |

---

## 🔧 Configuration

### `airflow_settings.yaml`

Used for **local development only**. Defines Airflow connections, variables, and pools without using the UI. See [Astronomer docs](https://www.astronomer.io/docs/astro/cli/develop-project#configure-airflow_settingsyaml-local-development-only).

### `docker-compose.override.yml`

Extends the default Astro `docker-compose.yml` to add:
- **MinIO** — object storage on ports `9000`/`9001`
- **Spark** master + worker on ports `7077`, `8081`, `8082`
- **Metabase** BI tool on port `3000`
- **docker-proxy** — exposes Docker socket safely on port `2376`

All services share the `ndsnet` bridge network.

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
  <sub>Built with ❤️ using Apache Airflow, Spark, MinIO, PostgreSQL & Metabase</sub>
</div>
