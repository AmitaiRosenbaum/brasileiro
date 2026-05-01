#!/bin/bash

# authenticate
export CR_PAT=<your-token-herer>
echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin

# build
docker build -t ghcr.io/amitairosenbaum/brasileiro-django:latest .

# push
docker push ghcr.io/amitairosenbaum/brasileiro-django:latest
