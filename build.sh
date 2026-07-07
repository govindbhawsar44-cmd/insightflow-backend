#!/usr/bin/env bash
export PRISMA_BINARY_CACHE_DIR="/opt/render/project/src/.prisma-binaries"

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

# Backup schema.prisma so it survives the persistent disk mount at runtime
cp prisma/schema.prisma schema_backup.prisma
