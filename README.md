# Selenium_Airflow
This repo use selenium with Airflow to schedule scraping task

- Currently supports channel_news_asia and wall_street_journal
- Script uses nodriver instead of undetected-chromedriver
- Scripts run asynchronously as nodriver is async


## Windows
- Mongodb setup: https://www.geeksforgeeks.org/how-to-install-mongodb-on-windows/
- Download docker desktop: https://www.docker.com/products/docker-desktop/
- `cd /path/airflow_tutorial`
- `docker build . --tag extending_airflow_tutorial:latest`
- `docker-compose up -d`
- Go to http://localhost:8080/