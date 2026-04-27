#!/bin/bash
set -e
set -x
scriptdir=$(cd $(dirname $0) && pwd)
project_name=$(basename "$scriptdir")
podman run -it --publish 127.0.0.1:8085:8080 ${project_name}:local 0.0.0.0
