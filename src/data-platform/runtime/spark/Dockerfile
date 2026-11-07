FROM apache/spark:4.0.0

USER root
WORKDIR /opt/spark/work-dir

COPY job_request.py sql_builder.py result_callback.py maintenance_runner.py main.py ./

USER spark
