#!/bin/bash
export DAGSTER_HOME=/Users/priyakarthik/MyProjects/MyNextJobInterview/LendingClub/Assignment/lc-pipeline-v1/dagster_home
source venv/bin/activate
dagster asset materialize --select '*' -m src.lending_club_pipeline.definitions 2>&1 | tail -50
