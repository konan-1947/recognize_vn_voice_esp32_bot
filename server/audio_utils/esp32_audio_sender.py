#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 Audio Sender Module
Gửi file WAV qua TCP tới ESP32 để phát âm thanh trên ESP32
"""

import socket
import time
import os
import threading
from typing import Optional, Callable

class ESP32AudioSender:
    """Class để gửi file âm thanh qua TCP tới ESP32"""
    
    def __init__(self, esp32_ip: str = "192.168.1.18", esp32_port: int = 8080, chunk_size: int = 1024):
        """
        Khởi tạo ESP32AudioSender
        
        Args:
            esp32_ip: IP address của ESP32
            esp32_port: Port TCP của ESP32 server
            chunk_size: Kích thước chunk để gửi dữ liệu
        """
        self.esp32_ip = esp32_ip
        self.esp32_port = esp32_port
        self.chunk_size = chunk_size
        
    def send_file_sync(self, wav_file_path: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Gửi file WAV đồng bộ qua TCP tới ESP32
        
        Args:
            wav_file_path: Đường dẫn tới file WAV
            progress_callback: Callback function để theo dõi tiến trình
            
        Returns:
            bool: True nếu gửi thành công, False nếu có lỗi
        """
        # 1. Kiểm tra file
        if not os.path.exists(wav_file_path):
            print(f"[ERROR] Không tìm thấy file: {wav_file_path}")
            return False
        
        filename = os.path.basename(wav_file_path)
        filesize = os.path.getsize(wav_file_path)
        print(f"[INFO] Chuẩn bị gửi file '{filename}' ({filesize} bytes) qua TCP.")

        # 2. Tạo socket TCP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # Timeout 10 giây

        try:
            # 3. Kết nối tới ESP32 Server
            print(f"[CONNECT] Đang kết nối tới {self.esp32_ip}:{self.esp32_port}...")
            sock.connect((self.esp32_ip, self.esp32_port))
            print("[CONNECT] Kết nối thành công!")

            # 4. Gửi header chứa thông tin file (tên file:kích thước\n)
            header = f"{filename}:{filesize}\n".encode('utf-8')
            sock.sendall(header)
            print(f"[SEND] Đã gửi header: {header.decode().strip()}")

            # 5. Gửi dữ liệu file
            bytes_sent = 0
            with open(wav_file_path, "rb") as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break  # Hết file
                    sock.sendall(chunk)
                    bytes_sent += len(chunk)
                    
                    # Gọi progress callback nếu có
                    if progress_callback:
                        progress_callback(bytes_sent, filesize)
                    
                    print(f"[SENDING] Đã gửi {bytes_sent}/{filesize} bytes...", end='\r')
            
            print(f"\n[SEND] Gửi file hoàn tất!")
            return True

        except ConnectionRefusedError:
            print("[ERROR] Kết nối bị từ chối. ESP32 server đã sẵn sàng chưa?")
            return False
        except socket.timeout:
            print("[ERROR] Timeout khi kết nối tới ESP32")
            return False
        except Exception as e:
            print(f"\n[ERROR] Gặp lỗi: {e}")
            return False
        finally:
            # 6. Đóng kết nối
            sock.close()
            print("[INFO] Đã đóng kết nối.")

    def send_file_async(self, wav_file_path: str, 
                       success_callback: Optional[Callable] = None,
                       error_callback: Optional[Callable] = None,
                       progress_callback: Optional[Callable] = None) -> threading.Thread:
        """
        Gửi file WAV bất đồng bộ qua TCP tới ESP32
        
        Args:
            wav_file_path: Đường dẫn tới file WAV
            success_callback: Callback khi gửi thành công
            error_callback: Callback khi có lỗi
            progress_callback: Callback để theo dõi tiến trình
            
        Returns:
            threading.Thread: Thread đang chạy
        """
        def _async_send():
            try:
                success = self.send_file_sync(wav_file_path, progress_callback)
                if success and success_callback:
                    success_callback(wav_file_path)
                elif not success and error_callback:
                    error_callback(f"Không thể gửi file {wav_file_path}")
            except Exception as e:
                if error_callback:
                    error_callback(f"Lỗi gửi file {wav_file_path}: {e}")
        
        thread = threading.Thread(target=_async_send, daemon=True)
        thread.start()
        return thread

    def test_connection(self) -> bool:
        """
        Test kết nối tới ESP32
        
        Returns:
            bool: True nếu có thể kết nối, False nếu không
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # Timeout 5 giây cho test
        
        try:
            sock.connect((self.esp32_ip, self.esp32_port))
            print(f"[TEST] Kết nối tới ESP32 {self.esp32_ip}:{self.esp32_port} thành công!")
            return True
        except Exception as e:
            print(f"[TEST] Không thể kết nối tới ESP32 {self.esp32_ip}:{self.esp32_port}: {e}")
            return False
        finally:
            sock.close()

# Convenience functions
def send_audio_to_esp32(wav_file_path: str, esp32_ip: str = "192.168.1.18", 
                       esp32_port: int = 8080) -> bool:
    """
    Hàm tiện ích để gửi file âm thanh đến ESP32
    
    Args:
        wav_file_path: Đường dẫn file WAV
        esp32_ip: IP của ESP32
        esp32_port: Port TCP của ESP32
        
    Returns:
        bool: True nếu gửi thành công
    """
    sender = ESP32AudioSender(esp32_ip, esp32_port)
    return sender.send_file_sync(wav_file_path)

def send_audio_to_esp32_async(wav_file_path: str, esp32_ip: str = "192.168.1.18", 
                             esp32_port: int = 8080,
                             on_success: Optional[Callable] = None,
                             on_error: Optional[Callable] = None) -> threading.Thread:
    """
    Hàm tiện ích để gửi file âm thanh đến ESP32 bất đồng bộ
    
    Args:
        wav_file_path: Đường dẫn file WAV
        esp32_ip: IP của ESP32
        esp32_port: Port TCP của ESP32
        on_success: Callback khi thành công
        on_error: Callback khi có lỗi
        
    Returns:
        threading.Thread: Thread đang chạy
    """
    sender = ESP32AudioSender(esp32_ip, esp32_port)
    return sender.send_file_async(wav_file_path, on_success, on_error)

# Test function
def main():
    """Test function"""
    sender = ESP32AudioSender()
    
    # Test kết nối
    if not sender.test_connection():
        print("Không thể kết nối tới ESP32")
        return
    
    # Test gửi file (cần có file test.wav)
    test_file = "test.wav"
    if os.path.exists(test_file):
        sender.send_file_sync(test_file)
    else:
        print(f"Không tìm thấy file test: {test_file}")

if __name__ == "__main__":
    main()