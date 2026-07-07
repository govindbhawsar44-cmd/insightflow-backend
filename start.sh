#!/usr/bin/env bash

# Ensure uploads directory exists
mkdir -p uploads

# Push DB schema to create dev.db if it doesn't exist at runtime
prisma db push --accept-data-loss

# Start the Uvicorn server, binding to the port provided by the host environment
python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
