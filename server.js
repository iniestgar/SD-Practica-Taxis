// server.js

const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const path = require('path');
const multer = require('multer'); // Importa multer para manejar archivos
const fs = require('fs'); // Importa fs para manejar archivos

// Configuración de multer
const upload = multer({ dest: 'uploads/' }); // Directorio temporal para guardar los archivos

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
    cors: {
        origin: "*", // Puedes restringir esto a tu front-end específico si lo deseas
        methods: ["GET", "POST"]
    }
});

// Middleware
app.use(cors());
app.use(express.json());

// Servir archivos estáticos del front-end
app.use(express.static(path.join(__dirname, '../front-end')));

// Ruta para servir EC.html
app.get('/EC.html', (req, res) => {
    res.sendFile(path.join(__dirname, '../../SD-Practica-Taxis-main/SD_2/EC.html'));
});

// Evento de conexión de Socket.IO
io.on('connection', (socket) => {
    console.log('Nuevo cliente conectado:', socket.id);

    socket.on('disconnect', () => {
        console.log('Cliente desconectado:', socket.id);
    });
});

// Endpoint para recibir logs desde la central en Python
app.post('/logs', (req, res) => {
    const { message } = req.body;

    if (!message) {
        return res.status(400).json({ error: 'El campo "message" es requerido.' });
    }

    // Emitir el mensaje a todos los clientes conectados
    io.emit('new_log', message);

    console.log('Log recibido y emitido:', message);
    res.status(200).json({ status: 'Log recibido y emitido.' });
});

// Endpoint para recibir el mapa desde la central
app.post('/map', upload.single('map'), (req, res) => {
    if (!req.file) {
        return res.status(400).send('No se recibió el mapa.');
    }

    try {
        const mapPath = path.resolve(req.file.path);
        const base64Image = `data:image/png;base64,${fs.readFileSync(mapPath).toString('base64')}`;
        io.emit('update_map', base64Image);  // Emitir el mapa a los clientes conectados

        fs.unlinkSync(mapPath);  // Eliminar el archivo temporal
        console.log('Mapa recibido y emitido correctamente.');
        res.status(200).send('Mapa recibido y emitido correctamente.');
    } catch (error) {
        console.error('Error al procesar el mapa:', error);
        res.status(500).send('Error al procesar el mapa.');
    }
});


// Iniciar el servidor en el puerto 3001
const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
    console.log(`Servidor Node.js corriendo en http://localhost:${PORT}`);
});
