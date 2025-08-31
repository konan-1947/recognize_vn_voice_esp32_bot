#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server Configuration - Tất cả các constants và cấu hình cho server
"""

from collections import deque
import threading

# ====== UDP CONFIG ======
HOST = "0.0.0.0"
UDP_PORT = 5005
FLASK_PORT = 5000
COMMAND_PORT = 5006  # Port để gửi lệnh về ESP32

# ====== WAKE WORD CONFIG ======
WAKE_WORD = "hello hello"  # Wake word để kích hoạt LED

# ====== AUDIO PROCESSING CONFIG ======
ENABLE_PREPROCESSING = True   # Bật preprocessing để cải thiện chất lượng
SILENCE_THRESHOLD = 0.01      # Tăng ngưỡng tiếng ồn (0.01 = 1%)
CIRCULAR_BUFFER_SIZE = 512000 # Circular buffer size (bytes) - 16.0s
LOOKBACK_SIZE = 128000        # Lookback trước khi phát hiện speech (bytes) - 4.0s
HIGH_PASS_ALPHA = 0.95        # High-pass filter coefficient
COMPRESSION_THRESHOLD = 0.3   # Dynamic range compression
COMPRESSION_RATIO = 4.0       # Compression ratio

# Điều chỉnh các ngưỡng để nhạy hơn:
MIN_SPEECH_RMS = 200          # Giảm từ 500 xuống 200 (nhạy hơn)
MIN_SILENCE_DURATION = 1.0    # Tăng từ 0.5s lên 1.0s để tránh cắt câu
MIN_AMPLITUDE_THRESHOLD = 1000  # Thêm ngưỡng amplitude mới

# Thêm ngưỡng silence detection:
SILENCE_RMS_THRESHOLD = 300   # Ngưỡng RMS để coi là silence
SILENCE_AMPLITUDE_THRESHOLD = 800  # Ngưỡng amplitude để coi là silence

# Thêm max recording duration:
MAX_RECORDING_DURATION = 10.0  # Tối đa 10 giây recording
MIN_API_CALL_DELAY = 1.0      # Delay tối thiểu giữa các lần gọi API (giây)

# ====== GOOGLE SPEECH CONFIG ======
GOOGLE_SPEECH_LANGUAGE = "vi-VN"  # Tiếng Việt
GOOGLE_SPEECH_TIMEOUT = 5         # Timeout 5 giây
GOOGLE_SPEECH_PHRASE_TIMEOUT = 1  # Timeout giữa các từ
GOOGLE_SPEECH_NON_SPEAKING_DURATION = 1.0  # Thời gian im lặng để kết thúc (tăng lên 1s)

# ====== GLOBAL VARIABLES ======
# Audio queue - shared between UDP listener and ASR worker
q_audio = deque(maxlen=1000)

# ESP32 address - updated when receiving UDP
esp32_address = None

# State variables for wake word detection
is_listening_for_question = False
question_logger = None

# Global shutdown event
shutdown_event = threading.Event()

# Logger instances
transcript_logger = None