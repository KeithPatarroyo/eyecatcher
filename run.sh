#!/bin/sh
# Wrapper so PORT from the environment is expanded by the shell (Railway/Heroku set PORT at runtime).
exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 1 --threads 4 eyecatcher.server:app
