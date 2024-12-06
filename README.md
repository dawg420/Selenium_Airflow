# Selenium_Airflow
This repo use selenium with Airflow to schedule scraping task

- Currently supports business_times, channel_news_asia, financial_times, reuters, straits_times, and wsj
- Script uses nodriver instead of undetected-chromedriver
- Scripts run asynchronously as nodriver is async


## Windows
- Mongodb setup: https://www.geeksforgeeks.org/how-to-install-mongodb-on-windows/
- Download docker desktop: https://www.docker.com/products/docker-desktop/
- `cd /path/airflow`
- `docker build . --tag extending_airflow_tutorial:latest`
- `docker-compose up -d`
- Go to http://localhost:8081/

##
- Current DAG logic:
  - All scraping processes are run in container `Chrome`.
  - `startup.sh` initialises scraping environment by setting up a virttual framebuffer `Xvfb`
  - All other scraping scripts depend on `startup.sh`, starts automatically after `startup.sh` is finished running