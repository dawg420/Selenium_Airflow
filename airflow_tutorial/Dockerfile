#Dockerfile
FROM apache/airflow:2.9.3-python3.10
# Install additional dependencies
USER root
COPY requirements.txt ./requirements.txt
RUN apt-get update && apt-get install -y docker.io
# Add the Airflow user to the docker group
RUN usermod -aG docker airflow
USER airflow
RUN pip install --upgrade pip
# Set up additional Python dependencies
RUN pip install --no-cache-dir -r ./requirements.txt