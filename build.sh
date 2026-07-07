#!/usr/bin/env bash
# Exit on error
set -o errexit

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Generate Prisma Client
prisma generate

# Push DB schema to create dev.db if it doesn't exist
prisma db push
