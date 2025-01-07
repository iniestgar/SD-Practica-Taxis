// EC_Registry.js

const express = require('express');
const app = express();
const https = require('https');
const fs = require('fs');
const mysql = require('mysql');
const { v4: uuidv4 } = require('uuid'); // Para generar tokens únicos
const cors = require('cors');

const minimist = require('minimist');

const args = minimist(process.argv.slice(2));

// Si no se pasan argumentos, asumir valores por defecto
const dbHost = args.db_host || 'localhost';
const dbUser = args.db_user || 'root';
const dbPassword = args.db_password || 'root';
const dbName = args.db_name || 'SD_MYSQL';
const IP = args.IP;

// Conectar a la base de datos con estos valores
const connection = mysql.createConnection({
  host: dbHost,
  user: dbUser,
  password: dbPassword,
  database: dbName,
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
// Endpoint para registrar un nuevo taxi
app.post('/taxis', (req, res) => {
  const { id_taxi, nombre, ciudad } = req.body;

  if (!id_taxi) {
    return res.status(400).json({ error: 'El id_taxi es requerido' });
  }

  // Comprobar si el id_taxi ya existe
  const checkSql = 'SELECT id_taxi FROM Taxis WHERE id_taxi = ?';
  connection.query(checkSql, [id_taxi], (error, results) => {
    if (error) {
      console.error('Error al comprobar el id_taxi:', error);
      return res.status(500).json({ error: 'Error al comprobar el id_taxi' });
    }

    if (results.length > 0) {
      // El id_taxi ya existe
      return res.status(409).json({ error: 'El id_taxi ya está en uso' });
    }

    // Crear objeto taxi con token null
    const taxiObj = {
      id_taxi: id_taxi,
      nombre: nombre || null,
      ciudad: ciudad || null,
      token: null, // Agregar esta línea
    };

    // Insertar en la base de datos
    const sql = 'INSERT INTO Taxis SET ?';
    connection.query(sql, taxiObj, (error) => {
      if (error) {
        console.error('Error al registrar el taxi:', error);
        return res.status(500).json({ error: 'Error al registrar el taxi' });
      }
      // Devolver confirmación al cliente
      res.status(201).json({ message: 'Taxi registrado correctamente', id_taxi: id_taxi });
    });
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
  key: fs.readFileSync('key.pem'),
  cert: fs.readFileSync('cert.pem'),
};

// Iniciar el servidor HTTPS
const port = 3000;
https.createServer(sslOptions, app).listen(port,IP, () => {
  console.log(`Servidor EC_Registry corriendo en https://${IP}:${port}`);
});
