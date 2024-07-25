#!/bin/sh

cd /app
/usr/bin/env uvicorn --host 0.0.0.0 --port 80 --workers 1 backend:app