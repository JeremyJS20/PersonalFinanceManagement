#!/bin/bash
echo "Building project deployments..."
python3 -m pip install -r requirements.txt --break-system-packages
echo "Running collectstatic..."
python3 manage.py collectstatic --noinput --clear
