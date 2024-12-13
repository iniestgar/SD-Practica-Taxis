const express = require('express');
const app = express();
const https = require('https');
const fs = require('fs');
const bodyParser = require("body-parser");
const axios = require('axios');
const readline = require('readline');



app.use(express.json()); // Para parsear solicitudes con cuerpo en formato JSON
// Crear aplicación Express
app.use(bodyParser.json());
// Configuración de API de OpenWeather
const OPENWEATHER_API_KEY = 'bfb5244f957c4c091acad44290dad571'; // Reemplaza con tu API key de OpenWeather
const OPENWEATHER_URL = 'https://api.openweathermap.org/data/2.5/weather';

// Configuración del servidor HTTPS
const PORT = 4000;
const CERT_PATH = "./CertificadoEC_CTC/certEC_CTC.pem"; // Ruta del certificado autofirmado


// Variable para almacenar la ciudad actual
let currentCity = "";

// Configurar readline para entrada del usuario
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

function promptCity() {
    rl.question("Por favor, introduce el nombre de la ciudad: ", (city) => {
        if (city.trim()) {
            currentCity = city.trim();
            console.log(`Ciudad actual configurada: ${currentCity}`);
        } else {
            console.log("La ciudad no puede estar vacía.");
        }
        promptCity(); // Preguntar nuevamente
    });
}

// Endpoint principal para obtener estado del tráfico
app.get('/city-traffic', async (req, res) => {
    if (!currentCity) {
        return res.status(400).json({ error: "No se ha configurado ninguna ciudad." });
    }

    try {
        // Llamada a la API de OpenWeather
        const response = await axios.get(OPENWEATHER_URL, {
            params: {
                q: currentCity,
                appid: OPENWEATHER_API_KEY,
                units: 'metric' // Para obtener la temperatura en grados Celsius
            }
        });

        const temperature = response.data.main.temp;
        const status = temperature < 0 ? "KO" : "OK";

        res.json({
            city: currentCity,
            temperature,
            status
        });
    } catch (error) {
        console.error("Error llamando a OpenWeather:", error.message);
        res.status(500).json({ error: "Error obteniendo información de OpenWeather" });
    }
});

// Arrancar el servidor HTTPS
https.createServer(
    {
        key: fs.readFileSync(CERT_PATH),
        cert: fs.readFileSync(CERT_PATH),
    },
    app
).listen(PORT, () => {
    console.log(`Servidor EC_CTC escuchando en https://localhost:${PORT}`);
    promptCity();
});
