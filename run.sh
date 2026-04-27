#!/bin/bash
set -e
set -x
scriptdir=$(cd $(dirname $0) && pwd)
project_name=$(basename "$scriptdir")
podman run -it --publish [::]:8085:8080 ${project_name}:local $*
