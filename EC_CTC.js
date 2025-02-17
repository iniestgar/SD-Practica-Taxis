const express = require('express');
const app = express();
const axios = require('axios');
const readline = require('readline');
const https = require('https');
const minimist = require('minimist');

const args = minimist(process.argv.slice(2));

// Configuración de la API de OpenWeather
const OPENWEATHER_API_KEY = 'bfb5244f957c4c091acad44290dad571'; // API key de OpenWeather
const OPENWEATHER_URL = 'https://api.openweathermap.org/data/2.5/weather';

// Configuración del servidor
const IP = args.ip
const PORT = 4000;
const CERT_PATH = "CertificadoEC_CTC/certEC_CTC.pem"; // Ruta del certificado autofirmado


// Variable para almacenar la ciudad actual
let currentCity = "";

// Configurar readline para la entrada del usuario
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});


// Función para pedir la ciudad al usuario
function promptCity() {
    rl.question("Por favor, introduce el nombre de la ciudad: ", (city) => {
        if (city.trim()) {
            currentCity = city.trim();
            console.log(`Ciudad actual configurada: ${currentCity}`);
        } else {
            console.log("La ciudad no puede estar vacía.");
        }
        promptCity(); // Volver a pedir la ciudad
    });
}

// Crear un agente HTTPS que ignore los errores de verificación del certificado
const httpsAgent = new https.Agent({
    rejectUnauthorized: false,
    requestCert: true
});

// Endpoint principal para obtener el estado del tráfico
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
            },
            httpsAgent
        });

        const temperature = response.data.main.temp;
        const status = temperature > 0 ? "SI" : "NO"; // Si la temperatura es mayor que 0, continuar tráfico

        res.json({
            city: currentCity,
            temperature,
            trafficAllowed: status // SI o NO
        });
    } catch (error) {
        console.error("Error llamando a OpenWeather:", error.message);
        res.status(500).json({ error: "Error obteniendo información de OpenWeather" });
    }
});

// Iniciar el servidor HTTP
app.listen(PORT,IP, () => {
    console.log(`Servidor EC_CTC escuchando en http://${IP}:${PORT}`);
    promptCity(); // Pedir la ciudad por consola
});
