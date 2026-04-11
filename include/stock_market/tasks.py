from airflow.hooks.base import BaseHook
import json

def _get_stock_prices(url, symbol):
    import requests

    url = f"{url}{symbol}?metrics=high?&interval=1d&range=1y"
    api = BaseHook.get_connection('stock_api')
    response = requests.get(url, headers=api.extra_dejson['headers'])
    return json.dumps(response.json()['chart']['result'][0])

def _store_prices(stock):
    from minio import Minio
    from io import BytesIO

    try:
        minio_conn = BaseHook.get_connection('minio')
        # Get endpoint and replace localhost with minio to work inside Docker network
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

def _get_formatted_csv(path):
    from minio import Minio

    try:
        minio_conn = BaseHook.get_connection('minio')
        # Get endpoint and replace localhost with minio to work inside Docker network
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
    bucket_name = 'stock-market'
    prefix_name = f"{path.split('/')[1]}/formatted_prices/"
    objects = client.list_objects(bucket_name, prefix=prefix_name, recursive=True)
    for obj in objects:
        if obj.object_name.endswith('.csv'):
            return f"{bucket_name}/{obj.object_name}"
    return AirflowNotFoundException("Formatted CSV not found")
