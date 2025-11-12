import cv2
import numpy as np
import time
import socketio  # untuk kirim data ke server.js

# === Koneksi ke server.js ===
sio = socketio.Client()
try:
    sio.connect("http://localhost:5000")  # ganti localhost dengan IP server jika terpisah
    print("🌐 Terhubung ke server.js untuk kirim midpoint")
except Exception as e:
    print("❌ Tidak bisa terhubung ke server.js:", e)

# === Setup Kamera ===
cap = cv2.VideoCapture(0)
cap.set(3, 320)  # Lebar
cap.set(4, 240)  # Tinggi

if not cap.isOpened():
    print("❌ Kamera tidak terdeteksi.")
    exit()
    
print("📸 Kamera aktif, kirim sinyal camera_ready ke server.js...")
sio.emit("camera_ready")  # 🔥 Kirim sinyal ke server.js agar Arduino diaktifkan

kernel = np.ones((5, 5), np.uint8)
print("📸 Deteksi jalur ASV aktif...")

last_send = 0  # untuk batasi pengiriman agar ringan

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    h, w = frame.shape[:2]

    # === Preprocessing ringan ===
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    # Mask merah
    lower_red1, upper_red1 = np.array([0, 95, 70]), np.array([12, 255, 255])
    lower_red2, upper_red2 = np.array([165, 95, 70]), np.array([180, 255, 255])
    mask_red = cv2.inRange(hsv, lower_red1, upper_red1) + cv2.inRange(hsv, lower_red2, upper_red2)

    # Mask hijau
    lower_green1, upper_green1 = np.array([30, 60, 50]), np.array([90, 255, 255])
    mask_green = cv2.inRange(hsv, lower_green1, upper_green1)

    # Kurangi noise
    mask_red = cv2.morphologyEx(mask_red, cv2.MORPH_CLOSE, kernel)
    mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_CLOSE, kernel)

    center_red, center_green = None, None

    # === Deteksi kontur merah ===
    contours_red, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours_red:
        if cv2.contourArea(cnt) > 300:
            x, y, wR, hR = cv2.boundingRect(cnt)
            center_red = (x + wR // 2, y + hR // 2)
            cv2.rectangle(frame, (x, y), (x + wR, y + hR), (0, 0, 255), 2)
            break

    # === Deteksi kontur hijau ===
    contours_green, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours_green:
        if cv2.contourArea(cnt) > 1800:
            x, y, wG, hG = cv2.boundingRect(cnt)
            center_green = (x + wG // 2, y + hG // 2)
            cv2.rectangle(frame, (x, y), (x + wG, y + hG), (0, 255, 0), 2)
            break

    # === Jika keduanya terdeteksi, buat garis dan titik tengah ===
    if center_red and center_green:
        # Gambar garis antara dua pusat warna
        cv2.line(frame, center_red, center_green, (255, 255, 0), 2)

        # Hitung titik tengah
        mid_x = (center_red[0] + center_green[0]) // 2
        mid_y = (center_red[1] + center_green[1]) // 2
        midpoint = (mid_x, mid_y)

        # Gambar titik bulat di tengah
        cv2.circle(frame, midpoint, 5, (255, 255, 255), -1)

        # Garis POV jalur ASV dari bawah tengah frame ke midpoint
        pov_start = (w // 2, h)
        cv2.line(frame, pov_start, midpoint, (0, 255, 255), 2)

        # === Kirim data titik tengah ke server.js setiap 0.3 detik ===
        if time.time() - last_send > 0.3:
            try:
                # format dikirim sesuai format Arduino: CENTER:<nilai_x>
                sio.emit("rudder-center", {"center": int(mid_x)})
                print(f"📡 Kirim ke server.js → Arduino: CENTER:{mid_x}")
                last_send = time.time()
            except Exception as e:
                print("⚠️ Gagal kirim data midpoint:", e)

    # === Tampilkan hasil ===
    cv2.imshow("ASV Vision", frame)

    # Tekan 'q' untuk keluar
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# === Cleanup ===
cap.release()
cv2.destroyAllWindows()
print("✅ Program selesai.")
