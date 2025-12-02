#!/bin/bash
export DAGSTER_HOME=/Users/priyakarthik/MyProjects/MyNextJobInterview/Banking/Assignment/banking-data-pipeline/dagster_home
source venv/bin/activate
dagster asset materialize --select '*' -m src.banking_pipeline.definitions 2>&1 | tail -50
