FROM docker.io/library/python:latest
ENV SOURCE_DATE_EPOCH=1700000000
COPY . /src
RUN python -m pip install build
RUN python -m pip install --no-deps -r /src/requirements.txt
RUN python -m build --skip-dependency-check --outdir /out /src
