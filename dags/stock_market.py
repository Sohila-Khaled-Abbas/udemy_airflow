from airflow.decorators import dag, task
from datetime import datetime

@dag (
    start_date=datetime(2023, 1, 1), 
    schedule="@daily", 
    catchup=False,
    tags = ['stock_market']
)
def stock_market():
    
    @task.sensor(poke_interval=30, timeout=600)
    def check_market_open():
        pass

stock_market()