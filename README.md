# 🌍 World Energy Orchestrated  
*Data Engineering Project with Apache Airflow, PostgreSQL, and Real Energy Data*

---

## 📖 Overview
This project demonstrates a modern **data engineering pipeline** that integrates:
- **Global energy statistics** from [Our World in Data](https://ourworldindata.org/energy)
- **Hourly power data for Denmark** from [Energi Data Service (Energinet)](https://www.energidataservice.dk/)
- A **PostgreSQL data warehouse**
- An **Apache Airflow** orchestrator (running in Docker)

The goal is to combine **static global datasets** with **live hourly data** to show how orchestration adds value to continuously updated sources.

---

## 🧱 Architecture
```
┌───────────────────────────────────────────────┐
│             Apache Airflow (Docker)           │
│  ├─ DAG #1: OWID Annual ETL                   │
│  └─ DAG #2: Energinet Hourly ETL (daily)      │
│                                               │
│        ↓ orchestrates                         │
│ PostgreSQL (Data Warehouse)                   │
│  ├─ silver: normalized tables (countries, etc)│
│  ├─ gold: materialized views / KPIs           │
│                                               │
│        ↓ visualization                        │
│ pgAdmin / Notebooks / PowerBI                 │
└───────────────────────────────────────────────┘
```

---

## ⚙️ Tech Stack
- **Docker** – containerization
- **Apache Airflow 3.1** – orchestration
- **PostgreSQL 16** – data warehouse
- **pgAdmin 8** – database management UI
- **Python** (pandas, requests, pyarrow) – data ingestion & transformation

---

## 🚀 Setup

### 1️⃣ Requirements
- Docker Desktop installed and running  
- macOS / Linux / Windows (tested on macOS)

### 2️⃣ Run Airflow + PostgreSQL + pgAdmin
```bash
docker compose build --no-cache
docker compose up airflow-init
docker compose up -d
```

Access:
- Airflow UI → [http://localhost:8080](http://localhost:8080)  (user: `airflow`, pass: `airflow`)
- pgAdmin UI → [http://localhost:8081](http://localhost:8081)  (user: `admin@example.com`, pass: `admin`)

### 3️⃣ Folder structure
```
world-energy-orchestrated/
├─ dags/             # Airflow DAGs
├─ data/             # datasets (OWID, Energinet)
├─ logs/             # Airflow logs
├─ plugins/          # custom plugins (optional)
├─ config/           # config files
├─ pgdata/           # PostgreSQL data (volume)
├─ docker-compose.yaml
├─ Dockerfile
├─ requirements.txt
├─ .env
└─ README.md
```

---

## 🧩 Project Phases

### Phase 1 – Global Energy DW (Our World in Data)
- Download global energy CSVs  
- Load into PostgreSQL (`silver.energy_fact_annual`)  
- Create materialized views:
  - `mv_transition_speed`
  - `mv_efficiency`
  - `mv_country_dashboard`

### Phase 2 – Denmark Hourly Orchestration (Energinet)
- Daily job fetching hourly power data (API)  
- Quality validation & upsert into `fact_power_hourly_dk`  
- Aggregation to monthly KPIs (`gold.mv_dk_energy_mix`)

---

## 🧠 Key Learnings
- Designing a **star-schema** for energy data  
- Using **Airflow** for orchestrating periodic updates  
- Building **materialized views** for KPIs  
- Combining **open datasets** with real-time feeds  
- Deploying **end-to-end** pipelines reproducibly in Docker

---

## 🧑‍💻 Author
**Roberto Cunego**  
Energy & Data Engineer — combining energy analysis with data-driven automation.  
[LinkedIn](https://www.linkedin.com/in/roberto-cunego/) • [GitHub](https://github.com/roberto-cunego)

---

## 📄 License
MIT License. Datasets © their respective providers.
