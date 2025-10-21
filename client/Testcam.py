import cv2

print("🔍 DAFTAR SEMUA KAMERA YANG TERDETEKSI:")
for i in range(0, 10):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        # Coba baca frame
        ret, frame = cap.read()
        if ret:
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            print(f"✅ Camera {i}: {int(width)}x{int(height)} - BISA BACA FRAME")
            
            # Tampilkan preview kecil
            cv2.imshow(f'Camera {i}', frame)
            cv2.waitKey(500)  # Tampilkan 0.5 detik
            cv2.destroyAllWindows()
        else:
            print(f"⚠️ Camera {i}: TERBUKA tapi GAGAL BACA FRAME")
        cap.release()
    else:
        print(f"❌ Camera {i}: TIDAK TERDETEKSI")

print("\n💡 Gunakan index kamera USB di webcam_client.py")