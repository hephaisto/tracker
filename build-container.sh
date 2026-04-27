#!/bin/bash
set -e
set -x

cache_flags=$1

scriptdir=$(cd $(dirname $0) && pwd)
project_name=$(basename "$scriptdir")

echo "### BUILDING WHEEL ###"
mkdir -p tmp/wheels
rm -rf tmp/wheels/*
build_container="build-${project_name}:latest"
podman build -f build.Containerfile -t ${build_container} .
container_id=$(podman create ${build_container})
podman cp "${container_id}:/out" ./tmp/wheels
podman rm "${container_id}"


echo "### BUILDING RUN-CONTAINER ###"
podman build ${cache_flags} -f run.Containerfile --build-arg=build_container=${build_container} -t ${project_name}:local .
