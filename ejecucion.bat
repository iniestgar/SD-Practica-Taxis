@echo off

:: Iniciar el servidor API central Node.js en el puerto 3001
echo Iniciando el servidor API central Node.js en el puerto 3001...
cd /d C:\SD2\SD-Practica-Taxis-main\central-api
start cmd /k "node server.js"
timeout /t 3

:: Iniciar el servidor EC_CTC en el puerto 4000
echo Iniciando el servidor EC_CTC en el puerto 4000...
cd /d C:\SD2\SD-Practica-Taxis-main\SD_3\SD_2
start cmd /k "node EC_CTC.js"
timeout /t 6

cd /d C:\SD2\SD-Practica-Taxis-main\SD_3\SD_2
:: Iniciar el servidor EC_Central
echo Iniciando el servidor EC_Central...
start cmd /k "python EC_Central.py 127.0.0.1 9090 EC_locations.json 127.0.0.1 9092"
timeout /t 4

:: Iniciar el servidor EC_Registry
echo Iniciando el servidor EC_Registry...
start cmd /k "node EC_Registry.js --db_host=localhost --db_user=root --db_password=hola --db_name=SD_MYSQL"
timeout /t 1

:: Iniciar los taxis y sensores
echo Iniciando el taxi EC_DE 1...
start cmd /k "python EC_DE.py 127.0.0.1 9090 127.0.0.1 3000 9093 127.0.0.1 9092 noauto"
timeout /t 1

echo Iniciando el sensor EC_S 1 para taxi 1...
start cmd /k "python EC_S.py 127.0.0.1 9093"
timeout /t 1

echo Iniciando el taxi EC_DE 2...
start cmd /k "python EC_DE.py 127.0.0.1 9090 127.0.0.1 3000 9094 127.0.0.1 9092 noauto"
timeout /t 1

echo Iniciando el sensor EC_S 2 para taxi 2...
start cmd /k "python EC_S.py 127.0.0.1 9094"
timeout /t 1

echo Iniciando el taxi EC_DE 3...
start cmd /k "python EC_DE.py 127.0.0.1 9090 127.0.0.1 3000 9095 127.0.0.1 9092 noauto"
timeout /t 1

echo Iniciando el sensor EC_S 3 para taxi 3...
start cmd /k "python EC_S.py 127.0.0.1 9095"
timeout /t 1

:: Iniciar los clientes
echo Iniciando el cliente EC_Customer 1...
start cmd /k "python EC_Customer.py 127.0.0.1 9092 cliente1_destinos.json"
timeout /t 2

echo Iniciando el cliente EC_Customer 2...
start cmd /k "python EC_Customer.py 127.0.0.1 9092 cliente2_destinos.json"
timeout /t 2

:: Abrir la página web del front-end en el navegador
echo Abriendo la página web del front-end...
start "http://localhost:3001/EC.html"
timeout /t 3

:: Fin del script
echo Todos los servicios han sido iniciados.
pause
