from airflow.hooks.base import BaseHook
from minio import Minio
from io import BytesIO
import json

def _get_stock_prices(url, symbol):
    import requests

    url = f"{url}{symbol}?metrics=high?&interval=1d&range=1y"
    api = BaseHook.get_connection('stock_api')
    response = requests.get(url, headers=api.extra_dejson['headers'])
    return json.dumps(response.json()['chart']['result'][0])

def _store_prices(stock):
    minio = BaseHook.get_connection('minio')
    client = Minio(
        endpoint=minio.extra_dejson['endpoint'].split('//')[1],  # fix: spilt → split
        access_key=minio.login,
        secret_key=minio.password,
        secure=False
    )
    bucket_name = 'stock-market'
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
    stock = json.loads(stock)
    symbol = stock['meta']['symbol']
    data = json.dumps(stock, ensure_ascii=False).encode('utf-8')  # fix: .encode() on the string
    objw = client.put_object(
        bucket_name=bucket_name,
        object_name=f'{symbol}/prices.json',
        data=BytesIO(data),       # fix: bytes go into BytesIO
        length=len(data),         # fix: len() of bytes
        content_type='application/json'
    )
    return f'{objw.bucket_name}/{symbol}'   # fix: variable not string literal