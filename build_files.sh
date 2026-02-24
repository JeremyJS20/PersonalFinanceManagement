#!/bin/bash
echo "Building project deployments..."
python3 -m pip install -r requirements.txt --break-system-packages

echo "Building Tailwind CSS..."
python3 manage.py tailwind install --no-input
python3 manage.py tailwind build --no-input

echo "Running collectstatic..."
python3 manage.py collectstatic --noinput --clear
