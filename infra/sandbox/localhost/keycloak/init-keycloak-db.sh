#!/bin/bash
set -e
psql -v ON_ERROR_STOP=0 --username "$POSTGRES_USER" -tc "SELECT 1 FROM pg_database WHERE datname = 'keycloak'" | grep -q 1 || psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -c "CREATE DATABASE keycloak"
