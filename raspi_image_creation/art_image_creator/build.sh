#!/bin/bash
set -eu
mkdir -p Kiosk_Image_Files/images Kiosk_Image_Files/logs
docker compose up --build
