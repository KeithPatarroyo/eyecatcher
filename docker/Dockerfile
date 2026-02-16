FROM python:3.12-slim

WORKDIR /app

# Install dependencies and package from pyproject.toml and src/
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir -e .

# Production WSGI server
RUN pip install --no-cache-dir gunicorn

# Config and static (data/ and output/ at runtime)
COPY config/ config/
COPY static/ static/

# output/ and data/ created at runtime; genealogy/community DBs created on first use
RUN mkdir -p output/saved data

# Wrapper script expands PORT at runtime (Railway runs startCommand without a shell)
COPY scripts/run.sh .
RUN chmod +x run.sh

ENV PORT=8080
EXPOSE 8080

CMD ["./run.sh"]
