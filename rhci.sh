#!/bin/bash
# Temporary script used for redhat-ci
set -xeuo pipefail
dnf -y install git gcc redhat-rpm-config python3-tox python3-virtualenv
python3-tox
