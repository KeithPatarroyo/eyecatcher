FROM python:3.11-slim

WORKDIR /app

# Install dependencies from pyproject.toml
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Production WSGI server
RUN pip install --no-cache-dir gunicorn

# Application code and config
COPY cppn_engine.py shader_compiler.py server.py .
COPY neat_config.txt neat_config_time.txt .
COPY interactive_viewer.html debug.js debug.css .

# Output directory for saved patterns
RUN mkdir -p output/saved data

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 server:app"]
