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

// =========================================================
//                SERIAL SETUP (AKTIF SAAT KAMERA READY)
// =========================================================
let port, parser;

function connectArduino() {
  if (port && port.isOpen) {
    console.log("ℹ️ Port sudah terbuka, abaikan koneksi ulang.");
    return;
  }

  port = new SerialPort({ path: "COM3", baudRate: 9600 });
  parser = port.pipe(new ReadlineParser({ delimiter: "\n" }));

  port.on("open", () => console.log("✅ Serial connected"));
  port.on("error", (err) => console.error("❌ Serial Error:", err));

  parser.on("data", handleSerialData);
}

// === Parsing Data GPS dari Arduino ===
function handleSerialData(line) {
  const clean = line.trim();
  if (!clean) return;

  console.log("📥 Serial:", clean);

  // Deteksi format GPS: LAT, LON, SOG, COG
  const regex =
    /LAT\s*:\s*([-+]?\d*\.?\d+),\s*LON\s*:\s*([-+]?\d*\.?\d+),\s*SOG\s*:\s*([-+]?\d*\.?\d+),\s*COG\s*:\s*([-+]?\d*\.?\d+)/i;
  const match = clean.match(regex);
  if (!match) return;

  const now = new Date();
  const formattedTime = now.toLocaleString("id-ID", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  const telemetry = {
    teamId: "TEAM_ASV_01",
    position: { lat: parseFloat(match[1]), lng: parseFloat(match[2]) },
    sog: parseFloat(match[3]),
    cog: parseFloat(match[4]),
    battery: dummyBattery.toFixed(1),
    mission: "14,8V",
    geotime: formattedTime,
  };

  teams.set(telemetry.teamId, telemetry);
  io.emit("real-time-update", telemetry);
}

// === Kirim waktu realtime tiap detik walau tanpa GPS ===
setInterval(() => {
  const now = new Date();
  const formattedTime = now.toLocaleString("id-ID", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  io.emit("time-update", { geotime: formattedTime });
}, 1000);

// =========================================================
//                        SOCKET.IO
// =========================================================
io.on("connection", (socket) => {
  connectedClients++;
  const clientIP = socket.handshake.address.replace("::ffff:", "");
  console.log(`🔗 Client connected (${clientIP}) — Total: ${connectedClients}`);

  // Kirim data terakhir ke client baru
  for (const [, telemetry] of teams.entries()) {
    socket.emit("real-time-update", telemetry);
  }

  if (connectedClients === 1) startBatteryDrain();

  // === Trigger dari Python YOLO: aktifkan koneksi Arduino ===
  socket.on("camera_ready", () => {
    console.log("🎥 Kamera siap, mengaktifkan koneksi Arduino...");
    connectArduino();
  });

  // === Perintah dari deteksi (rudder-center) ===
  socket.on("rudder-center", (data) => {
    if (!data || typeof data.center === "undefined" || !port) return;

    const cmd = `CENTER:${data.center}\n`;
    console.log("➡️ Kirim ke Arduino:", cmd.trim());
    port.write(cmd);
  });

  // === Perintah manual dari dashboard ===
  socket.on("rudder-command", (data) => {
    if (!data || !data.rudder || !port) return;

    const cmd = `RUDDER:${data.rudder}\n`;
    console.log("➡️ Manual ke Arduino:", cmd.trim());
    port.write(cmd);
  });

  socket.on("disconnect", () => {
    connectedClients--;
    stopBatteryDrain();
    console.log(`❌ Client disconnected (${clientIP})`);
  });
});

// =========================================================
//                        ROUTES
// =========================================================
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.get("/api/teams", (req, res) => {
  res.json(Array.from(teams.entries()));
});

// =========================================================
//                        START SERVER
// =========================================================
const PORT = process.env.PORT || 5000;
server.listen(PORT, "0.0.0.0", () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
