from airflow.decorators import dag, task
from airflow.sensors.base import PokeReturnValue
from airflow.hooks.base import BaseHook
from airflow.providers.docker.operators.docker import DockerOperator
from astro import sql as aql
from astro.files import File
from astro.sql.table import Table, Metadata
from datetime import datetime

from include.stock_market.tasks import _get_stock_prices, _store_prices, _get_formatted_csv

SYMBOL = 'AAPL'

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
    
    load_to_dw = aql.load_file_to_table(
        task_id='load_to_dw',
        input_file=File(
            path=f"s3://{BUCKET_NAME}/{{{{ti.xcom_pull(task_ids='get_formatted_csv')}}}}",
            conn_id='minio'
        ),
        output_table=Table(
            name='stock_prices', 
            conn_id='postgres',
            metadata=Metadata(
                schema='public'
            )
    ),
        load_options={
            'aws_access_key_id': BaseHook.get_connection('minio').login,
            'aws_secret_access_key': BaseHook.get_connection('minio').password,
            'endpoint_url': 'http://localhost:9000'
        }
    )
    
    stored >> format_prices >> formatted_csv >> load_to_dw
    

stock_market()
