#!/bin/bash

/opt/novnc/utils/novnc_proxy --vnc ${VNC_HOST}:${VNC_PORT} --listen ${PORT:-6080}