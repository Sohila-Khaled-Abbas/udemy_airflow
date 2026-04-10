from airflow.decorators import dag, task
from airflow.sensors.base import PokeReturnValue
from airflow.hooks.base import BaseHook
from datetime import datetime

from include.stock_market.tasks import _get_stock_prices, _store_prices

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
        return _store_prices(stock)  # fix: was calling itself recursively

    url = is_api_available()
    stock = get_stock_prices(url, SYMBOL)
    store_prices(stock)


stock_market()
