import express from 'express';
import http from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

const teams = new Map();

// 🔧 Simpan waktu frame terakhir untuk tiap tim
const lastFrameTime = {};

io.on('connection', (socket) => {
  console.log('🔗 Client connected:', socket.id);

  // Telemetry data handler
  socket.on('telemetry-data', (data) => {
    if (!data.teamId) return;
    if (!teams.has(data.teamId)) teams.set(data.teamId, {});
    teams.set(data.teamId, { ...teams.get(data.teamId), ...data });
    io.emit('real-time-update', data);
  });

  // 🖼️ Image stream handler
  socket.on('image-stream', (imageData) => {
    if (!imageData.teamId) return;

    const now = Date.now();
    const teamId = imageData.teamId;

    // ⏱️ Batasi FPS menjadi ~5 frame per detik per tim
    if (!lastFrameTime[teamId] || now - lastFrameTime[teamId] > 200) {
      io.emit(`team-${teamId}-image`, imageData);
      lastFrameTime[teamId] = now;
    }
  });

  socket.on('disconnect', () => {
    console.log('❌ Client disconnected:', socket.id);
  });
});

// Serve frontend
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// API untuk data tim
app.get('/api/teams', (req, res) => {
  res.json(Array.from(teams.entries()));
});

// Jalankan server
const PORT = process.env.PORT || 5000;
server.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 ASV Monitoring Server running on port ${PORT}`);
  console.log(`📊 Dashboard: http://localhost:${PORT}`);
  console.log('🌐 Accessible in LAN via http://<IP_RASPBERRY>:5000');
});
