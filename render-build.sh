#!/usr/bin/env bash
# Salir inmediatamente si ocurre un error
set -o errexit

# Instalar dependencias de Python
pip install -r requirements.txt

# Descargar Chromium e instalar sus dependencias en Linux
playwright install chromium
playwright install-deps

#comandos para desplegarlo en local
#docker docker run -p 8000:8000 huevbadge
#docker ps
#docker stop