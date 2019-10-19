#!/bin/bash

ENV="${OWLCAM_ENV:-dev}"

if [ $ENV == 'dev' ]; then
  $OWLCAM_PATH/venv/bin/python3 -m owlcam
else
  sudo -E bash -c "${OWLCAM_PATH}/venv/bin/python3 -m owlcam"
fi