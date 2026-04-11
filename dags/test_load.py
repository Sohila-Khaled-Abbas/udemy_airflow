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
except:
    endpoint = 'minio:9000'
    login = 'minio'
    password = 'minio123'

client = Minio(
    endpoint=endpoint,
    access_key=login,
    secret_key=password,
    secure=False
)

# get latest csv
objects = client.list_objects('stock-market', prefix='AAPL/formatted_prices/', recursive=True)
csv_files = [obj.object_name for obj in objects if obj.object_name.endswith('.csv')]
if not csv_files:
    print("CSV NOT FOUND IN MINIO")
    exit(1)
stock_market_csv_path = 'stock-market/' + csv_files[-1] 

parts = stock_market_csv_path.split('/', 1)
bucket_name = parts[0]
object_name = parts[1]

response = client.get_object(bucket_name, object_name)
df = pd.read_csv(io.BytesIO(response.data))
print("CSV Loaded. Rows:", len(df))

try:
    hook = PostgresHook(postgres_conn_id='postgres')
    hook.get_connection('postgres')
except Exception:
    hook = PostgresHook(postgres_conn_id='my_postgres')

engine = hook.get_sqlalchemy_engine()
df.to_sql('stock_prices', engine, schema='public', if_exists='replace', index=False)
print("SUCCESS!")
