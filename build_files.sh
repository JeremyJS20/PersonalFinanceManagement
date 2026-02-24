#!/bin/bash
echo "Building project deployments..."
python3.9 -m pip install -r requirements.txt
echo "Running collectstatic..."
python3.9 manage.py collectstatic --noinput --clear
