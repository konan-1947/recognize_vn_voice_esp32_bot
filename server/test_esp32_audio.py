#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script để gửi âm thanh tới ESP32
"""

import os
import sys
import time

# Thêm thư mục audio_utils vào Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'audio_utils'))

from audio_utils import ESP32AudioSender, send_audio_to_esp32, send_audio_to_esp32_async

def test_esp32_audio():
    """Test gửi file audio tới ESP32"""
    
    # Cấu hình ESP32
    ESP32_IP = "192.168.1.18"  # THAY BẰNG IP CỦA ESP32
    ESP32_PORT = 8080
    
    # File test (bạn cần có file test.wav)
    test_files = ["test.wav", "hello.wav", "response.wav"]
    
    print("=== TEST ESP32 AUDIO SENDER ===")
    
    # Test kết nối
    sender = ESP32AudioSender(ESP32_IP, ESP32_PORT)
    print("1. Test kết nối tới ESP32...")
    if not sender.test_connection():
        print("❌ Không thể kết nối tới ESP32. Kiểm tra:")
        print("   - ESP32 đã bật và kết nối WiFi chưa?")
        print("   - IP address đúng chưa?")
        print("   - ESP32 đã chạy code với TCP server chưa?")
        return
    
    print("✅ Kết nối ESP32 thành công!")
    
    # Test gửi file đồng bộ
    print("\n2. Test gửi file đồng bộ...")
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"Gửi file: {test_file}")
            success = send_audio_to_esp32(test_file, ESP32_IP, ESP32_PORT)
            if success:
                print(f"✅ Gửi {test_file} thành công!")
                time.sleep(3)  # Đợi phát xong
            else:
                print(f"❌ Lỗi gửi {test_file}")
            break
    else:
        print("❌ Không tìm thấy file test nào")
        print("Tạo file test.wav trong thư mục hiện tại để test")
        return
    
    # Test gửi file bất đồng bộ
    print("\n3. Test gửi file bất đồng bộ...")
    for test_file in test_files:
        if os.path.exists(test_file):
            def on_success(file_path):
                print(f"✅ Gửi async {file_path} thành công!")
            
            def on_error(error_msg):
                print(f"❌ Lỗi async: {error_msg}")
            
            print(f"Gửi file async: {test_file}")
            thread = send_audio_to_esp32_async(test_file, ESP32_IP, ESP32_PORT, on_success, on_error)
            thread.join()  # Đợi hoàn thành
            break
    
    print("\n=== TEST HOÀN TẤT ===")

def create_test_wav():
    """Tạo file WAV test đơn giản"""
    try:
        import numpy as np
        import scipy.io.wavfile as wavfile
        
        # Tạo âm thanh test (1 giây, 16kHz, mono)
        sample_rate = 16000
        duration = 1.0
        frequency = 440  # A4 note
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio = np.sin(2 * np.pi * frequency * t) * 0.3  # Volume 30%
        audio = (audio * 32767).astype(np.int16)  # Convert to 16-bit
        
        wavfile.write("test.wav", sample_rate, audio)
        print("✅ Đã tạo file test.wav")
        return True
        
    except ImportError:
        print("❌ Cần cài đặt numpy và scipy để tạo file test:")
        print("pip install numpy scipy")
        return False

if __name__ == "__main__":
    print("ESP32 Audio Sender Test")
    print("======================")
    
    # Kiểm tra file test
    test_file = "test.wav"
    if not os.path.exists(test_file):
        print(f"Không tìm thấy file {test_file}")
        print("Bạn có muốn tạo file test không? (y/n): ", end="")
        choice = input().lower()
        if choice == 'y':
            if create_test_wav():
                test_esp32_audio()
        else:
            print("Tạo file test.wav và chạy lại script")
    else:
        test_esp32_audio()