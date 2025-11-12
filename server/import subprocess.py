import subprocess
import time

print("🚀 Menjalankan server.js ...")
server = subprocess.Popen(["node", "server.js"])

# Tunggu agar server siap
time.sleep(5)

print("📸 Menjalankan deteksi kamera (importcv2.py)...")
try:
    subprocess.run(["python", "importcv2.py"])
except KeyboardInterrupt:
    print("\n🛑 Program dihentikan oleh user.")

# Jika importcv2.py selesai, hentikan server.js
print("🧹 Menutup server.js ...")
server.terminate()
