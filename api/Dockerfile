FROM docker-registry.mydomain/lab/happysct:base

WORKDIR /app

COPY api/entry.sh /app
COPY api/backend.py /app
COPY conf/*.json /app/conf/
COPY ops-metadata.yaml /app
COPY happysct.py /app
COPY rollout.py /app
COPY libs/*.py /app/libs/

EXPOSE 80
ENTRYPOINT ["/bin/sh", "/app/entry.sh"]
