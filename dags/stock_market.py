from airflow.decorators import dag, task
from airflow.sensors.base import PokeReturnValue
from airflow.hooks.base import BaseHook
from airflow.providers.docker.operators.docker import DockerOperator
from datetime import datetime

from include.stock_market.tasks import _get_stock_prices, _store_prices, _get_formatted_csv

SYMBOL = 'AAPL'
BUCKET_NAME = 'stock-market'

@dag(
    start_date=datetime(2023, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=['stock_market']
)
def stock_market():

    @task.sensor(poke_interval=30, timeout=300, mode='poke')
    def is_api_available() -> PokeReturnValue:
        import requests

        api = BaseHook.get_connection('stock_api')
        url = f"{api.host}{api.extra_dejson['endpoint']}"
        print(url)
        response = requests.get(url, headers=api.extra_dejson['headers'])
        condition = response.json()['finance']['result'] is None
        return PokeReturnValue(is_done=condition, xcom_value=url)

    @task
    def get_stock_prices(url, symbol):
        return _get_stock_prices(url, symbol)

    @task
    def store_prices(stock):
        return _store_prices(stock)

    format_prices = DockerOperator(
        task_id='format_prices',
        image='airflow/stock-app',
        container_name='format_prices',
        api_version='auto',
        auto_remove='success',
        docker_url='tcp://docker-proxy:2375',
        network_mode='container:spark-master',
        tty=True,
        xcom_all=False,
        mount_tmp_dir=False,
        environment={
            'SPARK_APPLICATION_ARGS': '{{ task_instance.xcom_pull(task_ids="store_prices") }}'
        }
    )
    
    @task
    def get_formatted_csv(path):
        return _get_formatted_csv(path)

    url = is_api_available()
    stock = get_stock_prices(url, SYMBOL)
    stored = store_prices(stock)
    
    formatted_csv = get_formatted_csv(stored)
    
    @task
    def load_to_dw(stock_market_csv_path: str):
        import io
        import pandas as pd
        from minio import Minio
        from airflow.hooks.base import BaseHook
        from airflow.providers.postgres.hooks.postgres import PostgresHook
        
        try:
            minio_conn = BaseHook.get_connection('minio')
            endpoint_url = minio_conn.extra_dejson.get('endpoint_url', minio_conn.extra_dejson.get('endpoint', 'http://minio:9000'))
            endpoint = endpoint_url.split('//')[1].replace('localhost', 'minio')
            login = minio_conn.login
            password = minio_conn.password
        except Exception:
            endpoint = 'minio:9000'
            login = 'minio'
            password = 'minio123'
            
        client = Minio(
            endpoint=endpoint,
            access_key=login,
            secret_key=password,
            secure=False
        )
        
        parts = stock_market_csv_path.split('/', 1)
        bucket_name = parts[0]
        object_name = parts[1]
        
        response = client.get_object(bucket_name, object_name)
        df = pd.read_csv(io.BytesIO(response.data))
        
        # Determine the postgres connection
        try:
            hook = PostgresHook(postgres_conn_id='postgres')
            hook.get_connection('postgres')
        except Exception:
            hook = PostgresHook(postgres_conn_id='my_postgres')
            
        engine = hook.get_sqlalchemy_engine()
        df.to_sql('stock_prices', engine, schema='public', if_exists='replace', index=False)
        
    loaded = load_to_dw(formatted_csv)
    
    stored >> format_prices >> formatted_csv >> loaded
    

stock_market()
