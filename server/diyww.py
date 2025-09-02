#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Speech Circular Server - Real-time speech recognition với ESP32 + INMP441
Sử dụng modular architecture với audio_utils components
"""

import threading
import time
import signal
import sys

# Import tất cả components từ audio_utils
from audio_utils import (
    # Core functionality
    check_audio_dependencies, TranscriptLogger,
    # Server components  
    create_app, create_templates, shutdown_event,
    # Processing threads
    udp_listener, asr_worker,
    # Configuration
    FLASK_PORT, transcript_logger, question_logger,
    # ESP32 Audio Sender
    ESP32AudioSender, send_audio_to_esp32, send_audio_to_esp32_async
)

def signal_handler(signum, frame):
    """Signal handler để graceful shutdown"""
    print(f"\n[SHUTDOWN] Nhận signal {signum}, đang dừng server...")
    shutdown_event.set()
    time.sleep(2)  # Đợi threads dừng
    print("[SHUTDOWN] Server đã dừng an toàn")
    sys.exit(0)

def send_audio_to_esp32_wrapper(wav_file_path: str, esp32_ip: str = "192.168.1.18", esp32_port: int = 8080) -> bool:
    """
    Hàm wrapper để gửi file âm thanh tới ESP32
    
    Args:
        wav_file_path: Đường dẫn tới file WAV
        esp32_ip: IP của ESP32 (mặc định: 192.168.1.18)
        esp32_port: Port TCP của ESP32 (mặc định: 8080)
    
    Returns:
        bool: True nếu gửi thành công
    """
    print(f"[ESP32_AUDIO] Đang gửi file {wav_file_path} tới ESP32 {esp32_ip}:{esp32_port}")
    return send_audio_to_esp32(wav_file_path, esp32_ip, esp32_port)

def send_audio_to_esp32_async_wrapper(wav_file_path: str, esp32_ip: str = "192.168.1.18", esp32_port: int = 8080):
    """
    Hàm wrapper để gửi file âm thanh tới ESP32 bất đồng bộ
    
    Args:
        wav_file_path: Đường dẫn tới file WAV
        esp32_ip: IP của ESP32 (mặc định: 192.168.1.18)
        esp32_port: Port TCP của ESP32 (mặc định: 8080)
    """
    def on_success(file_path):
        print(f"[ESP32_AUDIO] Gửi file {file_path} thành công!")
    
    def on_error(error_msg):
        print(f"[ESP32_AUDIO] Lỗi: {error_msg}")
    
    print(f"[ESP32_AUDIO] Đang gửi file {wav_file_path} tới ESP32 {esp32_ip}:{esp32_port} (async)")
    return send_audio_to_esp32_async(wav_file_path, esp32_ip, esp32_port, on_success, on_error)

def test_esp32_connection(esp32_ip: str = "192.168.1.18", esp32_port: int = 8080) -> bool:
    """
    Test kết nối tới ESP32
    
    Args:
        esp32_ip: IP của ESP32
        esp32_port: Port TCP của ESP32
    
    Returns:
        bool: True nếu kết nối thành công
    """
    sender = ESP32AudioSender(esp32_ip, esp32_port)
    return sender.test_connection()

def main():
    """Main function để khởi động server"""
    
    # Đăng ký signal handlers
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    # Kiểm tra dependencies
    if not check_audio_dependencies():
        print("[ERROR] Thiếu dependencies, vui lòng cài đặt trước")
        exit(1)
    
    # Khởi tạo global loggers
    import audio_utils.server_config as config
    config.transcript_logger = TranscriptLogger(output_dir="transcripts", filename="live_transcript.txt")
    print(f"[TRANSCRIPT] Logger: {config.transcript_logger.get_filepath()}")
    
    config.question_logger = TranscriptLogger(output_dir="transcripts", filename="questions.log")
    print(f"[QUESTION] Logger: {config.question_logger.get_filepath()}")
    
    # Tạo Flask app và SocketIO
    app, socketio = create_app()
    
    # Tạo templates directory
    create_templates()
    
    # Khởi động processing threads
    udp_thread = threading.Thread(target=udp_listener, daemon=True)
    asr_thread = threading.Thread(target=lambda: asr_worker(socketio), daemon=True)  # Pass socketio to asr_worker
    
    print("[UDP] Đang khởi động UDP Listener thread...")
    udp_thread.start()
    print("[UDP] UDP Listener thread đã khởi động")
    
    print("[ASR] Đang khởi động ASR Worker thread...")
    asr_thread.start()
    print("[ASR] ASR Worker thread đã khởi động với Circular Buffer")
    
    # Kiểm tra threads có alive không
    time.sleep(2)
    if asr_thread.is_alive():
        print("[ASR] ASR Worker thread đang chạy bình thường")
    else:
        print("[ERROR] ASR Worker thread đã dừng!")
    
    # Chạy Flask-SocketIO server
    print("[FLASK] Khởi động Flask-SocketIO server...")
    try:
        socketio.run(app, host="0.0.0.0", port=FLASK_PORT, debug=False)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Nhận Ctrl+C, đang dừng server...")
        shutdown_event.set()
        time.sleep(2)
        print("[SHUTDOWN] Server đã dừng an toàn")
    except Exception as e:
        print(f"[ERROR] Lỗi Flask server: {e}")
        shutdown_event.set()
        time.sleep(2)
        print("[SHUTDOWN] Server đã dừng an toàn")

if __name__ == "__main__":
    main()