#!/usr/bin/env bash

# Ensure uploads directory exists
mkdir -p uploads

# Start the Uvicorn server, binding to the port provided by the host environment
python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
