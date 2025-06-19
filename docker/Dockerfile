FROM python:3.13.5-slim
LABEL description.short="STAC Populator"
LABEL description.long="Utility to populate STAC Catalog, Collections and Items from various dataset/catalog sources."
LABEL maintainer="Francis Charette-Migneault <francis.charette-migneault@crim.ca>"
LABEL vendor="CRIM"
LABEL version="0.8.0"

# setup paths
ENV APP_DIR=/opt/local/src/stac-populator
ENV PYESSV_ARCHIVE_HOME=/home/stac/.esdoc/pyessv-archive/

WORKDIR ${APP_DIR}

# obtain source files
COPY STACpopulator/ ${APP_DIR}/STACpopulator/
COPY README.md LICENSE pyproject.toml ${APP_DIR}/

# install runtime/package dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        netbase \
        git \
    && mkdir -p "$(dirname "${PYESSV_ARCHIVE_HOME}")" \
    && git clone "https://github.com/ES-DOC/pyessv-archive" "${PYESSV_ARCHIVE_HOME}" \
    && pip install --no-cache-dir ${APP_DIR} \
    && apt-get remove -y \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r stac && useradd -r -g stac stac
USER stac

ENTRYPOINT ["stac-populator"]
