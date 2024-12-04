@echo off
echo Iniciando Apache Zookeeper...
start cmd /k "C:\kafka\kafkaSD\bin\windows\zookeeper-server-start.bat C:\kafka\kafkaSD\config\zookeeper.properties"
timeout /t 15 /nobreak

echo Iniciando Kafka Broker...
start cmd /k "C:\kafka\kafkaSD\bin\windows\kafka-server-start.bat C:\kafka\kafkaSD\config\server.properties"
