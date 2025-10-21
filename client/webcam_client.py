import cv2
import socketio
import base64
import time
import random
from datetime import datetime

# Socket.io client
sio = socketio.Client(reconnection_attempts=5, reconnection_delay=1000)

@sio.event
def connect():
    print("✅ TERHUBUNG KE SERVER! Data akan dikirim ke http://localhost:5000")

@sio.event
def connect_error(data):
    print(f"❌ GAGAL TERHUBUNG KE SERVER: {data}")
    print("💡 Pastikan 'node server.js' sudah jalan di Terminal lain!")

@sio.event
def disconnect():
    print("❌ TERPUTUS DARI SERVER")

def test_server_connection():
    """Test koneksi ke server"""
    import requests
    try:
        response = requests.get('http://localhost:5000', timeout=5)
        if response.status_code == 200:
            print("🌐 Server terdeteksi dan responsive")
            return True
        else:
            print(f"❌ Server merespon dengan status: {response.status_code}")
            return False
    except requests.ConnectionError:
        print("❌ SERVER TIDAK TERDETEKSI!")
        print("   Jalankan di Terminal 1: cd server && node server.js")
        return False
    except Exception as e:
        print(f"❌ Error test server: {e}")
        return False

def setup_usb_webcam():
    """Setup webcam USB 2.0 di index 1"""
    print("🎦 SETUP WEBCAM USB 2.0...")
    
    # FORCE PAKAI CAMERA 1 (USB 2.0)
    camera_index = 1
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"❌ Tidak bisa buka camera {camera_index}")
        # Fallback ke camera 0
        camera_index = 0
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print("❌ Tidak ada kamera yang bisa dibuka")
            return None, -1
        else:
            print(f"⚠️  Pakai camera {camera_index} (bukan USB)")
    else:
        print(f"✅ WEBCAM USB 2.0 ditemukan di index {camera_index}")
    
    # Set resolusi tinggi untuk USB
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # Test baca frame
    ret, frame = cap.read()
    if not ret:
        print("❌ Camera terbuka tapi gagal baca frame")
        cap.release()
        return None, -1
    
    print(f"🎯 Webcam USB 2.0 siap: 1280x720 @ 30FPS")
    return cap, camera_index

def get_sensor_data(current_phase):
    """Generate data sensor realistis"""
    if current_phase <= 1:
        balls_passed = 0
    elif current_phase == 2:
        balls_passed = random.randint(1, 5)
    elif current_phase == 3:
        balls_passed = random.randint(6, 10)
    else:
        balls_passed = 10

    imaging_score = 5 if current_phase >= 4 else 0
    docking_score = 5 if current_phase >= 6 else 0
    
    return {
        'battery': max(20, 100 - int(time.time() / 15) % 80),
        'position': {
            'lat': -6.2 + random.uniform(-0.001, 0.001),
            'lng': 106.8 + random.uniform(-0.001, 0.001)
        },
        'sog': round(1.5 + random.random() * 4, 2),
        'cog': random.randint(0, 360),
        'signalStrength': random.randint(80, 95),
        'ballsPassed': balls_passed,
        'imagingScore': imaging_score,
        'dockingScore': docking_score,
        'penaltyCount': random.randint(0, 2),
        'missionTime': int(time.time())
    }

def main():
    print("=" * 60)
    print("🚀 ASV WEBCAM CLIENT - WEBCAM USB 2.0")
    print("=" * 60)
    
    # 1. TEST SERVER DULU
    if not test_server_connection():
        return
    
    # 2. SETUP WEBCAM USB 2.0
    cap, camera_index = setup_usb_webcam()
    if cap is None:
        return

    # 3. CONNECT KE SERVER
    print("🔗 Menghubungkan ke server...")
    try:
        sio.connect('http://localhost:5000', wait_timeout=10)
        print("✅ BERHASIL TERHUBUNG KE SERVER!")
    except Exception as e:
        print(f"❌ Gagal connect: {e}")
        cap.release()
        return

    print("📡 Mulai streaming data real-time...")
    print("💡 Tekan 'Q' di window kamera untuk berhenti")

    mission_phases = [
        "🚀 Preparation & System Check",
        "🧭 Navigation to Ball Set 1", 
        "🎾 Reading Ball Set 1-5",
        "🎾 Reading Ball Set 6-10",
        "📷 Surface Imaging Mission",
        "🌊 Underwater Imaging Mission",
        "⚓ Docking Procedure",
        "✅ Mission Complete"
    ]
    current_phase = 0
    last_image_time = 0
    frame_count = 0
    start_time = time.time()

    try:
        while True:
            # Baca frame dari webcam USB
            ret, frame = cap.read()
            if not ret:
                print("❌ Gagal membaca frame dari webcam USB")
                break

            frame_count += 1
            
            # Resize tetap 1280x720 (HD quality)
            frame = cv2.resize(frame, (1280, 720))

            # Update mission phase setiap 12 detik
            elapsed_time = time.time() - start_time
            new_phase = min(int(elapsed_time / 12), len(mission_phases) - 1)
            if new_phase != current_phase:
                current_phase = new_phase
                print(f"🔄 Fase: {mission_phases[current_phase]}")

            # Prepare telemetry data
            sensor_data = get_sensor_data(current_phase)
            telemetry_data = {
                'teamId': 'ASV_TEAM_01',
                'timestamp': datetime.now().isoformat(),
                'position': sensor_data['position'],
                'sog': sensor_data['sog'], 
                'cog': sensor_data['cog'],
                'battery': sensor_data['battery'],
                'signalStrength': sensor_data['signalStrength'],
                'missionPhase': mission_phases[current_phase],
                'ballsPassed': sensor_data['ballsPassed'],
                'imagingScore': sensor_data['imagingScore'],
                'dockingScore': sensor_data['dockingScore'],
                'penaltyCount': sensor_data['penaltyCount'],
                'missionTime': sensor_data['missionTime']
            }
            
            # Kirim data telemetry
            sio.emit('telemetry-data', telemetry_data)

            # Kirim gambar setiap 2 detik (lebih sering)
            current_time = time.time()
            if current_time - last_image_time >= 2:
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret:
                    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                    sio.emit('image-stream', {
                        'teamId': 'ASV_TEAM_01',
                        'cameraType': 'surface', 
                        'imageData': jpg_as_text,
                        'timestamp': datetime.now().isoformat(),
                        'missionPhase': mission_phases[current_phase]
                    })
                    print(f"🖼️ Kirim gambar HD - Balls: {sensor_data['ballsPassed']}/10 - Battery: {sensor_data['battery']}%")
                    last_image_time = current_time

            # Tampilkan preview
            cv2.imshow(f'ASV Webcam USB 2.0 - {mission_phases[current_phase]} - Press Q', frame)
            
            # Stop jika tekan Q
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            time.sleep(0.05)  # Lebih responsif
            
    except KeyboardInterrupt:
        print("\n🛑 Dihentikan oleh user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        sio.disconnect()
        print("✅ Webcam USB 2.0 dilepaskan")
        print("🎯 Client dihentikan")

if __name__ == "__main__":
    main()