#!/bin/bash
set -e
set -x

scriptdir=$(cd $(dirname $0) && pwd)
project_name=$(basename "$scriptdir")

podman run --mount type=bind,src=${scriptdir},target=/src,ro --entrypoint '["bash", "-c", "python -m pip install pytest-asyncio && python -m pytest -o cache_dir=/root /src"]' ${project_name}:local
