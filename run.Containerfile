FROM docker.io/library/python:latest
ARG build_container

COPY ./requirements.txt /requirements.txt
RUN python -m pip install --no-deps -r /requirements.txt

# The application comes last since it will be updated every commit
# because the git revision changes. Even if you have high update rates
# for the lockfile, the wheel will change every build anyway.
COPY --from=${build_container} /out/*.whl /wheels/
RUN python -m pip install --no-deps /wheels/*.whl


ENTRYPOINT ["run-web-ui"]
