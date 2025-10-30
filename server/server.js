import express from "express";
import http from "http";
import { Server } from "socket.io";
import cors from "cors";
import path from "path";
import { fileURLToPath } from "url";
import { SerialPort } from "serialport";
import { ReadlineParser } from "@serialport/parser-readline";

// === Path Setup ===
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// === Express + Socket.io ===
const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: "*", methods: ["GET", "POST"] },
});

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

// === Global Data ===
const teams = new Map();
const lastFrameTime = {};
let dummyBattery = 100;
let connectedClients = 0;
let batteryInterval = null;

// === Battery Simulation ===
function startBatteryDrain() {
  if (batteryInterval) return;
  batteryInterval = setInterval(() => {
    dummyBattery = Math.max(0, dummyBattery - 1);
    console.log(`⚡ Battery: ${dummyBattery}%`);
  }, 60000);
}

function stopBatteryDrain() {
  if (batteryInterval && connectedClients === 0) {
    clearInterval(batteryInterval);
    batteryInterval = null;
    console.log("🛑 Battery drain stopped (no clients)");
  }
}

// === Serial Port Setup ===
// Ganti path sesuai perangkat kamu:
// Raspberry Pi biasanya: "/dev/ttyUSB0"
const port = new SerialPort({ path: "COM3", baudRate: 9600 });
const parser = port.pipe(new ReadlineParser({ delimiter: "\n" }));

port.on("open", () => console.log("✅ Serial connected"));
port.on("error", (err) => console.error("❌ Serial Error:", err));

// === Parsing Data GPS dari Arduino ===
// Format contoh: LAT:-6.129765,LON:106.834950,SOG:2.53,COG:87.41
parser.on("data", (line) => {
  const clean = line.trim();
  if (!clean) return;
  console.log("📥 Serial:", clean);

  const regex =
    /LAT\s*:\s*([-+]?\d*\.?\d+),\s*LON\s*:\s*([-+]?\d*\.?\d+),\s*SOG\s*:\s*([-+]?\d*\.?\d+),\s*COG\s*:\s*([-+]?\d*\.?\d+)/i;
  const match = clean.match(regex);
  if (!match) return console.log("⚠️ Format salah:", clean);

  const telemetry = {
    teamId: "TEAM_ASV_01",
    position: { lat: parseFloat(match[1]), lng: parseFloat(match[2]) },
    sog: parseFloat(match[3]),
    cog: parseFloat(match[4]),
    battery: dummyBattery.toFixed(1),
    mission: "Navigation",
    geotime: new Date().toISOString(),
  };

  teams.set(telemetry.teamId, telemetry);
  io.emit("real-time-update", telemetry);
  console.log("📡 Data terkirim:", telemetry);
});

// === Socket.IO ===
io.on("connection", (socket) => {
  connectedClients++;
  const clientIP = socket.handshake.address.replace("::ffff:", "");
  console.log(`🔗 Client connected (${clientIP}) — Total: ${connectedClients}`);

  // Kirim data terakhir ke client baru
  for (const [, telemetry] of teams.entries()) {
    socket.emit("real-time-update", telemetry);
  }

  if (connectedClients === 1) startBatteryDrain();

  // === TERIMA STREAM GAMBAR DARI LOKALHOST SAJA ===
  socket.on("image-stream", (data) => {
    const now = Date.now();
    const teamId = data.teamId || "TEAM_ASV_01";

    // Hanya izinkan dari device lokal
    if (clientIP !== "127.0.0.1" && clientIP !== "::1") {
      console.log(`🚫 Stream dari IP ${clientIP} ditolak (bukan localhost)`);
      return;
    }

    if (!data.image) return;
    if (!lastFrameTime[teamId] || now - lastFrameTime[teamId] > 80) {
      io.emit(`team-${teamId}-image`, data);
      lastFrameTime[teamId] = now;
      console.log(`📸 Frame diterima dari ${teamId} (${data.image.length} bytes)`);
    }
  });

  socket.on("disconnect", () => {
    connectedClients--;
    console.log(`❌ Client disconnected (${clientIP}) — ${connectedClients} left`);
    stopBatteryDrain();
  });
});

// === ROUTES ===
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.get("/api/teams", (req, res) => {
  res.json(Array.from(teams.entries()));
});

// === Start Server ===
const PORT = process.env.PORT || 5000;
server.listen(PORT, "0.0.0.0", () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`🌐 Dashboard: http://localhost:${PORT}`);
});
