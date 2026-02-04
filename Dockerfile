FROM python:3.11-slim

WORKDIR /app

# Install dependencies from pyproject.toml
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Production WSGI server
RUN pip install --no-cache-dir gunicorn

# Application code and config
COPY cppn_engine.py shader_compiler.py server.py stateless_api.py community_routes.py genome_serialization.py genome_visualizer.py .
COPY neat_config.txt neat_config_time.txt .
COPY interactive_viewer.html debug.js debug.css storage.js population_ui.js community.js community.css viewer.css pattern_renderer.js .
COPY data/ data/

# Output directory for saved patterns
RUN mkdir -p output/saved data

# Wrapper script expands PORT at runtime (Railway runs startCommand without a shell)
COPY run.sh .
RUN chmod +x run.sh

ENV PORT=8080
EXPOSE 8080

CMD ["./run.sh"]
