from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.postgres.operators.postgres import PostgresOperator
import pandas as pd
import requests
import io
import os

OWID_URL = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"
DATA_DIR = "/opt/airflow/data"
RAW_CSV_PATH = os.path.join(DATA_DIR, "owid_energy_raw.csv")

def download_raw():
    # 1) scarica il CSV OWID così com'è (grezzo)
    resp = requests.get(OWID_URL, timeout=60)
    resp.raise_for_status()
    with open(RAW_CSV_PATH, "w", encoding="utf-8") as f:
        f.write(resp.text)
    return RAW_CSV_PATH

def load_bronze(file_path: str, truncate_before_load: bool = False):
    """
    2) carica il CSV grezzo in bronze.owid_energy_raw SENZA trasformazioni.
       Opzione: truncate per run 'full-refresh'.
    """
    hook = PostgresHook(postgres_conn_id="dw_postgres")
    conn = hook.get_conn()
    cur = conn.cursor()

    if truncate_before_load:
        cur.execute("TRUNCATE TABLE bronze.owid_energy_raw;")

    # usa COPY per performance
    with open(file_path, "r", encoding="utf-8") as f:
        cur.copy_expert(
            sql="""
                COPY bronze.owid_energy_raw(
                    iso_code, country, continent, year,
                    primary_energy_consumption, electricity_generation,
                    renewables_share_electricity, energy_per_capita,
                    population, gdp_per_capita
                )
                FROM STDIN WITH (FORMAT CSV, HEADER TRUE)
            """,
            file=f,
        )
    conn.commit()
    cur.close()
    conn.close()

# 3) trasformazione SQL: bronze -> silver (solo conversioni & upsert su dim + fact)
SQL_BRONZE_TO_SILVER = """
-- upsert nazioni
INSERT INTO silver.dim_country(iso_code, country_name, continent)
SELECT DISTINCT iso_code, country, continent
FROM bronze.owid_energy_raw
WHERE iso_code IS NOT NULL
ON CONFLICT (iso_code) DO UPDATE
SET country_name = EXCLUDED.country_name,
    continent    = EXCLUDED.continent;

-- fact annuale normalizzato (unità coerenti)
-- NB: usiamo ON CONFLICT DO UPDATE per idempotenza (iso_code, year)
INSERT INTO silver.fact_energy_annual(
  iso_code, year,
  primary_energy_consumption_twh,
  electricity_generation_twh,
  renewable_electricity_share,
  energy_per_capita_mwh,
  population_million,
  gdp_per_capita
)
SELECT
  r.iso_code,
  r.year,
  r.primary_energy_consumption / 1_000_000.0,  -- da MWh a TWh (OWID usa MWh)
  r.electricity_generation   / 1_000_000.0,    -- da MWh a TWh
  r.renewables_share_electricity,
  r.energy_per_capita,                         -- già MWh per capita
  r.population / 1_000_000.0,                  -- in milioni
  r.gdp_per_capita
FROM bronze.owid_energy_raw r
WHERE r.iso_code IS NOT NULL
  AND r.year IS NOT NULL
ON CONFLICT (iso_code, year) DO UPDATE
SET primary_energy_consumption_twh = EXCLUDED.primary_energy_consumption_twh,
    electricity_generation_twh     = EXCLUDED.electricity_generation_twh,
    renewable_electricity_share    = EXCLUDED.renewable_electricity_share,
    energy_per_capita_mwh          = EXCLUDED.energy_per_capita_mwh,
    population_million             = EXCLUDED.population_million,
    gdp_per_capita                 = EXCLUDED.gdp_per_capita;

-- refresh delle MV gold (veloci; se crescono molto usa CONCURRENTLY)
REFRESH MATERIALIZED VIEW gold.mv_transition_speed;
REFRESH MATERIALIZED VIEW gold.mv_energy_per_capita_trend;
"""

default_args = {
    "owner": "roberto",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="owid_energy_dag",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,       # lo lanciamo a mano (OWID è annuale)
    catchup=False,
    tags=["owid", "energy", "bronze-silver"],
) as dag:

    t1_download = PythonOperator(
        task_id="download_raw_csv",
        python_callable=download_raw,
    )

    t2_load_bronze = PythonOperator(
        task_id="load_bronze_raw",
        python_callable=load_bronze,
        op_kwargs={
            "file_path": "{{ ti.xcom_pull(task_ids='download_raw_csv') }}",
            "truncate_before_load": True   # metti False se vuoi append-only
        }
    )

    t3_transform_to_silver = PostgresOperator(
        task_id="bronze_to_silver",
        postgres_conn_id="dw_postgres",
        sql=SQL_BRONZE_TO_SILVER,
    )

    t1_download >> t2_load_bronze >> t3_transform_to_silver
