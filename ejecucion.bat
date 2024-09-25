@echo off
echo Iniciando el servidor EC_Central...
start cmd /k "python EC_Central.py 127.0.0.1 9090 localizaciones.txt"
timeout /t 3

echo Iniciando el taxi EC_DE...
start cmd /k "python EC_DE.py 127.0.0.1 9090 9091"
timeout /t 3

echo Iniciando el sensor EC_S...
start cmd /k "python EC_S.py 127.0.0.1 9091"
