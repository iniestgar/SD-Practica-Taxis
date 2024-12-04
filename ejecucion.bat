@echo off
echo Iniciando el servidor EC_Central...
start cmd /k "python EC_Central.py 127.0.0.1 9090 EC_locations.json 127.0.0.1 9092"
timeout /t 8

@echo off
echo Iniciando el servidor EC_Registry...
cd /d C:\SD2\SD-Practica-Taxis-main\SD_2
start cmd /k "node EC_Registry.js"
timeout /t 3

echo Iniciando el taxi EC_DE 1...
start cmd /k "python EC_DE.py 127.0.0.1 9090 127.0.0.1 3000 9093 127.0.0.1 9092 noauto"
"
timeout /t 3

echo Iniciando el sensor EC_S 1 para taxi 1...
start cmd /k "python EC_S.py 127.0.0.1 9093"
timeout /t 3

echo Iniciando el taxi EC_DE 2...
start cmd /k "python EC_DE.py 127.0.0.1 9090 127.0.0.1 3000 9094 127.0.0.1 9092 noauto"
"
timeout /t 3

echo Iniciando el sensor EC_S 2 para taxi 2...
start cmd /k "python EC_S.py 127.0.0.1 9094"
timeout /t 3

echo Iniciando el taxi EC_DE 3...
start cmd /k "python EC_DE.py 127.0.0.1 9090 127.0.0.1 3000 9095 127.0.0.1 9092 noauto"
"
timeout /t 3

echo Iniciando el sensor EC_S 3 para taxi 3...
start cmd /k "python EC_S.py 127.0.0.1 9095"
timeout /t 3

echo Iniciando el cliente EC_Customer 1...
start cmd /k "python EC_Customer.py 127.0.0.1 9092 cliente1_destinos.json"
timeout /t 3

echo Iniciando el cliente EC_Customer 2...
start cmd /k "python EC_Customer.py 127.0.0.1 9092 cliente2_destinos.json"
timeout /t 3

