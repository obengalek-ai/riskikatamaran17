import cv2
import numpy as np
import socketio
import time
import base64

# === Koneksi ke server Socket.IO ===
sio = socketio.Client()

while True:
    try:
        sio.connect('http://127.0.0.1:5000')  # Ganti IP jika server.js di device lain
        print("⚙️  Connected to ASV Dashboard (server.js aktif)")
        break
    except Exception as e:
        print(f"Menunggu server.js... ({e})")
        time.sleep(2)

# === Inisialisasi kamera ===
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Kamera tidak terdeteksi.")
    exit()

print("📸 Deteksi warna aktif... Tekan CTRL + C atau ESC untuk berhenti.\n")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # Konversi ke HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # === Mask warna merah ===
        lower_red1 = np.array([0, 120, 70])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 120, 70])
        upper_red2 = np.array([180, 255, 255])
        mask_red = cv2.inRange(hsv, lower_red1, upper_red1) + cv2.inRange(hsv, lower_red2, upper_red2)

        # === Mask warna hijau ===
        lower_green = np.array([40, 50, 50])
        upper_green = np.array([85, 255, 255])
        mask_green = cv2.inRange(hsv, lower_green, upper_green)

        warna = "NONE"

        # === Deteksi warna merah ===
        contours_red, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours_red:
            area = cv2.contourArea(cnt)
            if area > 1500:
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                cv2.putText(frame, "MERAH", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                warna = "MERAH"

        # === Deteksi warna hijau ===
        contours_green, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours_green:
            area = cv2.contourArea(cnt)
            if area > 1500:
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, "HIJAU", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                warna = "HIJAU"

        # === Tampilkan status warna di pojok kiri atas ===
        cv2.putText(frame, f"WARNA TERDETEKSI: {warna}",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(frame, f"WARNA TERDETEKSI: {warna}",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                    (0, 0, 255) if warna == "MERAH" else (0, 255, 0) if warna == "HIJAU" else (100, 100, 100),
                    2, cv2.LINE_AA)

        # === Encode frame ke base64 untuk dikirim ke web ===
        _, buffer = cv2.imencode('.jpg', frame)
        image_data = base64.b64encode(buffer).decode('utf-8')

        # Kirim ke server.js
        sio.emit("kamera-stream", {"image": image_data, "color": warna})

        # === Preview kamera ===
        cv2.imshow("Deteksi Warna - ASV Dashboard", frame)
        if cv2.waitKey(1) == 27:  # Tekan ESC untuk keluar
            break

except KeyboardInterrupt:
    print("\n🛑 Dihentikan oleh user (Ctrl + C).")

finally:
    cap.release()
    cv2.destroyAllWindows()
    sio.disconnect()
    print("✅ Kamera & koneksi Socket.IO ditutup dengan aman.")
