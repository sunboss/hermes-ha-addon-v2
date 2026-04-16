ARG HERMES_IMAGE_DIGEST="sha256:0ee58988876f5bb3d6e8e664542bbad2eb9453b9f8ef9a669afc87316087b357"
FROM nousresearch/hermes-agent@${HERMES_IMAGE_DIGEST}

ENV HERMES_HOME=/data
ENV HERMES_INSTALL_DIR=/opt/hermes
ENV PATH=/opt/hermes/.venv/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV ADDON_UI_PORT=8099
ENV DASHBOARD_HOST=127.0.0.1
ENV DASHBOARD_PORT=9119

RUN uv pip install --python /opt/hermes/.venv/bin/python --no-cache \
    "fastapi>=0.115,<1" "uvicorn[standard]>=0.30,<1" "PyYAML>=6,<7"

COPY bootstrap.py /opt/hermes-ha-addon/bootstrap.py
COPY run.py /opt/hermes-ha-addon/run.py
COPY hermes_ui /opt/hermes-ha-addon/hermes_ui

ENTRYPOINT ["python3", "/opt/hermes-ha-addon/run.py"]
