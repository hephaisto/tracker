#!/bin/bash
set -e
set -x

scriptdir=$(cd $(dirname $0) && pwd)
venv_dir=$(pwd)/.run-venv
mkdir -p "${venv_dir}"
podman run --mount type=bind,src=${scriptdir},target=/src,ro --mount type=bind,src=${venv_dir},target=/venv --publish 8085:8080 -it docker.io/library/python:latest bash -c "python -m venv /venv && /venv/bin/python -m pip install --no-deps /src -r /src/requirements.txt && /venv/bin/python -m python_podman_dependabot_test.cmdline 0.0.0.0"
