import sys

import pendulum
sys.path.append(r'../')
from airflow import DAG
# from airflow.providers.docker.operators.docker import DockerOperator
from airflow.operators.bash import BashOperator
# from docker.types import Mount

default_args = {
    'owner': 'airflow',
    'start_date': pendulum.today('UTC').add(days=-1),
}

with DAG(
    dag_id='selenium_dag',
    default_args=default_args,
    schedule=None,
    catchup=False,
) as dag:

    run_startup_script = BashOperator(
        task_id='run_startup_script',
        bash_command="{{ 'docker exec airflow_tutorial-chrome-1 /scripts/startup.sh' | safe }}"
    )


    run_startup_script