#!/bin/sh

set -eu

cd "$(dirname "$0")/../.."

rm -rf dist/*
./tools/scripts/create_package.sh
podman build --squash-all --tag android-parser .
rm -f dist/image-android-parser.tar
podman save --output dist/image-android-parser.tar android-parser
cd dist/
tar -czf langpack-android-parser.tar.gz image-android-parser.tar