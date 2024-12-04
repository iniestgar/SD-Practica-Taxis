// EC_Registry.js

const express = require('express');
const app = express();
const https = require('https');
const fs = require('fs');
const mysql = require('mysql');
const cors = require('cors');

// Configuración de la conexión a la base de datos MySQL
const connection = mysql.createConnection({
  host: '127.0.0.1',
  user: 'root',
  password: '6633',
  database: 'sd_bbdd',
});

// Conectar a la base de datos
connection.connect((error) => {
  if (error) {
    console.error('Error al conectar a la base de datos:', error);
    return;
  }
  console.log('Conexión a la base de datos SD_MYSQL correcta');
});

// Middleware
app.use(express.json()); // Para parsear solicitudes con cuerpo en formato JSON
app.use(cors()); // Para habilitar CORS si es necesario

// Endpoint para registrar un nuevo taxi
app.post('/taxis', (req, res) => {
  // Generar un ID de taxi aleatorio (número y letra, e.g., '1a')
  const randomNum = Math.floor(Math.random() * 100) + 1; // Número entre 1 y 100
  const randomLetter = String.fromCharCode(97 + Math.floor(Math.random() * 26)); // Letra entre 'a' y 'z'
  const taxiID = `${randomNum}${randomLetter}`;

  // Obtener datos adicionales del cuerpo de la solicitud
  const { nombre, ciudad } = req.body;

  // Crear objeto taxi
  const taxiObj = {
    id_taxi: taxiID,
    nombre: nombre || null,
    ciudad: ciudad || null,
  };

  // Insertar en la base de datos
  const sql = 'INSERT INTO Taxis SET ?';
  connection.query(sql, taxiObj, (error) => {
    if (error) {
      console.error('Error al registrar el taxi:', error);
      res.status(500).json({ error: 'Error al registrar el taxi' });
      return;
    }
    // Devolver el ID y el token al cliente
    res.json({ id_taxi: taxiID });
  });
});

// Endpoint para obtener un taxi específico
app.get('/taxis/:id_taxi', (req, res) => {
  const id_taxi = req.params.id_taxi;
  const sql = 'SELECT id_taxi, nombre, ciudad FROM Taxis WHERE id_taxi = ?';
  connection.query(sql, [id_taxi], (error, results) => {
    if (error) {
      console.error('Error al obtener el taxi:', error);
      res.status(500).json({ error: 'Error al obtener el taxi' });
      return;
    }
    if (results.length > 0) {
      res.json(results[0]);
    } else {
      res.status(404).json({ error: 'Taxi no encontrado' });
    }
  });
});

// Endpoint para obtener todos los taxis
app.get('/taxis', (req, res) => {
  const sql = 'SELECT id_taxi, nombre, ciudad FROM Taxis';
  connection.query(sql, (error, results) => {
    if (error) {
      console.error('Error al obtener los taxis:', error);
      res.status(500).json({ error: 'Error al obtener los taxis' });
      return;
    }
    res.json(results);
  });
});

// Endpoint para actualizar información de un taxi
app.put('/taxis/:id_taxi', (req, res) => {
  const id_taxi = req.params.id_taxi;
  const { nombre, ciudad } = req.body;
  const sql = 'UPDATE Taxis SET nombre = ?, ciudad = ? WHERE id_taxi = ?';
  connection.query(sql, [nombre, ciudad, id_taxi], (error, results) => {
    if (error) {
      console.error('Error al actualizar el taxi:', error);
      res.status(500).json({ error: 'Error al actualizar el taxi' });
      return;
    }
    if (results.affectedRows > 0) {
      res.json({ message: 'Taxi actualizado correctamente' });
    } else {
      res.status(404).json({ error: 'Taxi no encontrado' });
    }
  });
});

// Endpoint para eliminar un taxi
app.delete('/taxis/:id_taxi', (req, res) => {
  const id_taxi = req.params.id_taxi;
  const sql = 'DELETE FROM Taxis WHERE id_taxi = ?';
  connection.query(sql, [id_taxi], (error, results) => {
    if (error) {
      console.error('Error al eliminar el taxi:', error);
      res.status(500).json({ error: 'Error al eliminar el taxi' });
      return;
    }
    if (results.affectedRows > 0) {
      res.json({ message: 'Taxi eliminado correctamente' });
    } else {
      res.status(404).json({ error: 'Taxi no encontrado' });
    }
  });
});

// Leer los certificados SSL
const sslOptions = {
  key: fs.readFileSync('certServ.pem'),
  cert: fs.readFileSync('certServ.pem'),
};

// Iniciar el servidor HTTPS
const port = 3000;
https.createServer(sslOptions, app).listen(port, () => {
  console.log(`Servidor EC_Registry corriendo en https://localhost:${port}`);
});
