@echo off
echo Iniciando el servidor EC_Central...
start cmd /k "python EC_Central.py localhost 9090 localizaciones.txt localhost 9092"
timeout /t 8

echo Iniciando el taxi EC_DE 1...
start cmd /k "python EC_DE.py 127.0.0.1 9090 9093 localhost 9092"
timeout /t 3

echo Iniciando el sensor EC_S 1 para taxi 1...
start cmd /k "python EC_S.py 127.0.0.1 9093"
timeout /t 3

echo Iniciando el taxi EC_DE 2...
start cmd /k "python EC_DE.py 127.0.0.1 9090 9094 localhost 9092"
timeout /t 3

echo Iniciando el sensor EC_S 2 para taxi 2...
start cmd /k "python EC_S.py 127.0.0.1 9094"
timeout /t 3

echo Iniciando el taxi EC_DE 3...
start cmd /k "python EC_DE.py 127.0.0.1 9090 9095 localhost 9092"
timeout /t 3

echo Iniciando el sensor EC_S 3 para taxi 3...
start cmd /k "python EC_S.py 127.0.0.1 9095"
timeout /t 3

echo Iniciando el cliente EC_Customer 1...
start cmd /k "python EC_Customer.py localhost 9092"
timeout /t 3

echo Iniciando el cliente EC_Customer 2...
start cmd /k "python EC_Customer.py localhost 9092"
timeout /t 3
