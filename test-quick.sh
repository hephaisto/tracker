#!/bin/bash
set -e
set -x

scriptdir=$(cd $(dirname $0) && pwd)
venv_dir=$(pwd)/.test-venv
mkdir -p "${venv_dir}"
podman run --mount type=bind,src=${scriptdir},target=/src,ro --mount type=bind,src=${venv_dir},target=/venv -it docker.io/library/python:latest bash -c "python -m venv /venv && /venv/bin/python -m pip install --no-deps /src -r /src/requirements.txt && /venv/bin/python -m pip install pytest-asyncio && /venv/bin/python -m pytest /src"
