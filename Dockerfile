FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY lyre/ ./lyre/

# In Docker, config is loaded from /root/.config/lyre/config.env.
# Mount it at runtime or pass environment variables via --env-file.
ENV XDG_CONFIG_HOME=/root/.config

ENTRYPOINT ["python", "-m", "lyre"]
