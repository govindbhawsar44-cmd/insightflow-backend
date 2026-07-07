#!/usr/bin/env bash
# Start the Uvicorn server, binding to the port provided by the host environment
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
