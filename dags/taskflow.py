from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def _task_a():
    print("Task A")
    return 42
    
def _task_b():
    print("Task B")
    print(ti.xcom_pull(task_ids='task_a'))
    
def _task_c():
    print("Task C")
    print(ti.xcom_pull(task_ids='task_b'))
    
with DAG(
    dag_id='taskflow', 
    start_date=datetime(2023, 1, 1), 
    schedule='@daily', 
    catchup=False,
    tags=['taskflow']
):
    task_a = PythonOperator(
        task_id='task_a', 
        python_callable=_task_a
        )
    task_b = PythonOperator(
        task_id='task_b', 
        python_callable=_task_b
        )
    task_c = PythonOperator(
        task_id='task_c',
        python_callable=_task_c
        )
    
    task_a >> task_b >> task_c    
