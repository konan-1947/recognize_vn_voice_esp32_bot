#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 + INMP441 Real-time Streaming Server với Google Speech Recognition + Circular Buffer
Sử dụng circular buffer với lookback để không bị cụt câu
"""

import socket
import struct
import threading
import queue
import json
import time
import os
import tempfile
import numpy as np
import speech_recognition as sr
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# ====== UDP CONFIG ======
HOST = "0.0.0.0"
UDP_PORT = 5005
FLASK_PORT = 5000
q_audio = queue.Queue()

# ====== AUDIO PROCESSING CONFIG ======
ENABLE_PREPROCESSING = True   # Bật preprocessing để cải thiện chất lượng
SILENCE_THRESHOLD = 0.01      # Tăng ngưỡng tiếng ồn (0.01 = 1%)
CIRCULAR_BUFFER_SIZE = 512000 # Circular buffer size (bytes) - 16.0s
LOOKBACK_SIZE = 128000        # Lookback trước khi phát hiện speech (bytes) - 4.0s
HIGH_PASS_ALPHA = 0.95        # High-pass filter coefficient
COMPRESSION_THRESHOLD = 0.3   # Dynamic range compression
COMPRESSION_RATIO = 4.0       # Compression ratio
MIN_SPEECH_RMS = 500          # Ngưỡng RMS tối thiểu để coi là speech (nhạy hơn)
MIN_SILENCE_DURATION = 1.0    # Thời gian im lặng tối thiểu để kết thúc câu (giây)

# ====== GOOGLE SPEECH CONFIG ======
GOOGLE_SPEECH_LANGUAGE = "vi-VN"  # Tiếng Việt
GOOGLE_SPEECH_TIMEOUT = 5         # Timeout 5 giây
GOOGLE_SPEECH_PHRASE_TIMEOUT = 1  # Timeout giữa các từ
GOOGLE_SPEECH_NON_SPEAKING_DURATION = 0.5  # Thời gian im lặng để kết thúc

# ====== Flask + SocketIO ======
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    """Trang chủ với giao diện real-time transcript"""
    return render_template("index.html")

@app.route('/status')
def status():
    """API trạng thái server"""
    return {
        "status": "running",
        "speech_engine": "Google Speech Recognition + Circular Buffer",
        "language": GOOGLE_SPEECH_LANGUAGE,
        "udp_port": UDP_PORT,
        "flask_port": FLASK_PORT,
        "audio_queue_size": q_audio.qsize()
    }

@app.route('/test')
def test():
    """Test kết nối"""
    return {"message": "Server hoạt động bình thường", "timestamp": time.time()}

def audio_preprocessing(audio_data):
    """Xử lý âm thanh nâng cao để cải thiện độ chính xác"""
    try:
        # Chuyển bytes thành numpy array
        samples = np.frombuffer(audio_data, dtype=np.int16)
        
        # 1. Normalize audio
        samples = samples.astype(np.float32) / 32768.0
        
        # 2. DC offset removal (loại bỏ offset DC)
        samples = samples - np.mean(samples)
        
        # 3. High-pass filter để loại bỏ tiếng ồn tần số thấp
        alpha = HIGH_PASS_ALPHA
        filtered = np.zeros_like(samples)
        filtered[0] = samples[0]
        for i in range(1, len(samples)):
            filtered[i] = alpha * (filtered[i-1] + samples[i] - samples[i-1])
        
        # 4. Dynamic range compression (nén động)
        threshold = COMPRESSION_THRESHOLD
        ratio = COMPRESSION_RATIO
        compressed = np.where(
            np.abs(filtered) > threshold,
            np.sign(filtered) * (threshold + (np.abs(filtered) - threshold) / ratio),
            filtered
        )
        
        # 5. Chuyển về int16
        processed_samples = (compressed * 32767).astype(np.int16)
        
        return processed_samples.tobytes()

    except Exception as e:
        print(f"Lỗi audio preprocessing: {e}")
        return audio_data

def save_audio_to_wav(audio_data, sample_rate=16000):
    """Lưu audio data thành file WAV tạm thời"""
    try:
        import wave
        
        # Đảm bảo audio data có độ dài chẵn (16-bit = 2 bytes)
        if len(audio_data) % 2 != 0:
            audio_data = audio_data[:-1]  # Bỏ byte cuối nếu lẻ
        
        # Tạo file WAV tạm thời
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
            
        # Tạo WAV file với format chính xác
        with wave.open(temp_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)
        
        print(f"✅ WAV file created: {temp_path}, size: {len(audio_data)} bytes, samples: {len(audio_data)//2}")
        return temp_path
        
    except Exception as e:
        print(f"❌ Lỗi tạo WAV file: {e}")
        return None

def transcribe_with_google_speech(audio_file_path):
    """Sử dụng Google Speech Recognition để nhận dạng giọng nói"""
    try:
        # Khởi tạo recognizer
        recognizer = sr.Recognizer()
        
        # Cấu hình parameters tối ưu
        recognizer.energy_threshold = 100  # Giảm ngưỡng năng lượng
        recognizer.dynamic_energy_threshold = True  # Tự động điều chỉnh
        recognizer.pause_threshold = 0.8  # Giảm pause threshold
        recognizer.non_speaking_duration = 0.3  # Giảm non-speaking duration
        recognizer.phrase_threshold = 0.3  # Thêm phrase threshold
        recognizer.operation_timeout = 10  # Tăng timeout
        
        # Đọc audio file
        with sr.AudioFile(audio_file_path) as source:
            print(f"🎤 Đang đọc audio file: {audio_file_path}")
            # Điều chỉnh cho ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.1)
            audio = recognizer.record(source)
        
        # Nhận dạng với Google Speech
        print(f"🔄 Đang gửi đến Google Speech API...")
        start_time = time.time()
        
        text = recognizer.recognize_google(
            audio,
            language=GOOGLE_SPEECH_LANGUAGE,
            show_all=False  # Chỉ lấy kết quả tốt nhất
        )
        
        processing_time = time.time() - start_time
        print(f"✅ Google Speech xử lý xong trong {processing_time:.2f}s")
        
        return text.strip()
        
    except sr.UnknownValueError:
        print("🔇 Google Speech không thể nhận dạng được giọng nói")
        print("💡 Có thể do: audio quá ngắn, tiếng ồn cao, hoặc không có giọng nói")
        return ""
    except sr.RequestError as e:
        print(f"❌ Lỗi Google Speech API: {e}")
        return ""
    except Exception as e:
        print(f"❌ Lỗi xử lý Google Speech: {e}")
        return ""

def udp_listener():
    """Thread lắng nghe UDP audio từ ESP32"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, UDP_PORT))
    print(f"🎧 UDP Audio server đang lắng nghe trên {HOST}:{UDP_PORT}")
    print(f"📡 Đang chờ audio packets từ ESP32...")
    
    packet_count = 0
    
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            packet_count += 1
            
            if packet_count % 100 == 0:  # Log mỗi 100 packets
                print(f"📦 Nhận {packet_count} packets từ {addr}")
            
            if len(data) <= 12: 
                continue
                
            # Parse header ESP32: seq(4) + time_ms(4) + codec(1) + len24(3)
            try:
                seq, time_ms, codec, len_b2, len_b1, len_b0 = struct.unpack_from("<IIBBBB", data, 0)
                length = (len_b2 << 16) | (len_b1 << 8) | len_b0
                payload = data[12:12+length]
                
                if len(payload) == length:
                    q_audio.put((payload, time_ms, seq))
                    
            except struct.error as e:
                # Nếu không parse được header, coi như raw audio
                q_audio.put((data, int(time.time() * 1000), 0))
                
        except Exception as e:
            print(f"❌ Lỗi UDP listener: {e}")
            continue

def asr_worker():
    """Thread xử lý ASR với Google Speech Recognition + Circular Buffer"""
    print("🎤 ASR Worker đã sẵn sàng xử lý audio với Google Speech Recognition + Circular Buffer...")
    print(f"📊 Cấu hình: circular_buffer_size={CIRCULAR_BUFFER_SIZE}, lookback_size={LOOKBACK_SIZE}")
    print(f"🌐 Ngôn ngữ: {GOOGLE_SPEECH_LANGUAGE}")
    
    # Circular buffer với lookback
    circular_buffer = bytearray(CIRCULAR_BUFFER_SIZE)
    buffer_head = 0  # Vị trí hiện tại trong buffer
    buffer_tail = 0  # Vị trí bắt đầu speech
    is_recording = False  # Trạng thái đang record
    consecutive_silence_count = 0
    max_silence_count = 15
    
    processed_chunks = 0
    
    while True:
        try:
            chunk, timestamp, seq = q_audio.get()
            processed_chunks += 1
            
            if processed_chunks % 50 == 0:  # Log mỗi 50 chunks
                print(f"🔄 ASR Worker: Đã xử lý {processed_chunks} chunks, buffer size: {len(circular_buffer)} bytes")
            
            # Kiểm tra tiếng ồn (silence detection) với circular buffer
            if len(chunk) >= 2:
                samples = struct.unpack(f"<{len(chunk)//2}h", chunk)
                rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
                max_amp = max(abs(s) for s in samples)
                is_speech = (rms > MIN_SPEECH_RMS) or (max_amp > 2000)
                
                # Thêm chunk vào circular buffer
                chunk_size = len(chunk)
                for i in range(chunk_size):
                    circular_buffer[buffer_head] = chunk[i]
                    buffer_head = (buffer_head + 1) % CIRCULAR_BUFFER_SIZE
                
                if is_speech:
                    if not is_recording:
                        # Bắt đầu record, lùi lại LOOKBACK_SIZE
                        buffer_tail = (buffer_head - LOOKBACK_SIZE) % CIRCULAR_BUFFER_SIZE
                        if buffer_tail < 0:
                            buffer_tail = 0
                        is_recording = True
                        print(f"🎤 Bắt đầu record: RMS={rms:.1f}, Max={max_amp}, Tail={buffer_tail}, Head={buffer_head}")
                    else:
                        # Đang record, cập nhật tail nếu cần để lấy câu dài hơn
                        current_tail = (buffer_head - LOOKBACK_SIZE) % CIRCULAR_BUFFER_SIZE
                        if current_tail < 0:
                            current_tail = 0
                        # Chỉ cập nhật tail nếu nó gần head hơn (để lấy câu dài)
                        if (buffer_head - current_tail) % CIRCULAR_BUFFER_SIZE > (buffer_head - buffer_tail) % CIRCULAR_BUFFER_SIZE:
                            buffer_tail = current_tail
                            print(f"🎤 Cập nhật tail: {buffer_tail} để lấy câu dài hơn")
                    
                    consecutive_silence_count = 0
                else:
                    consecutive_silence_count += 1
                    if consecutive_silence_count % 50 == 0:  # Log mỗi 50 lần
                        print(f"🔇 Silence: {consecutive_silence_count} consecutive, RMS={rms:.1f}, Max={max_amp}")
                    
                    # Nếu silence đủ lâu và đang record, đánh dấu để xử lý
                    silence_duration = consecutive_silence_count * 0.02  # 20ms per chunk
                    if silence_duration >= MIN_SILENCE_DURATION and is_recording:
                        print(f"🔇 Silence đủ lâu ({silence_duration:.1f}s), đánh dấu xử lý...")
                        # Không continue, để tiếp tục xử lý ở phần dưới
                    
                    # Chỉ continue nếu chưa đủ silence
                    if silence_duration < MIN_SILENCE_DURATION:
                        continue
            
            # Xử lý khi có silence đủ lâu và đang record
            silence_duration = consecutive_silence_count * 0.02  # 20ms per chunk
            should_process = (is_recording and silence_duration >= MIN_SILENCE_DURATION)
            
            if should_process:
                # Trích xuất audio từ circular buffer (từ tail đến head)
                if buffer_head >= buffer_tail:
                    # Buffer không bị wrap
                    audio_data = bytes(circular_buffer[buffer_tail:buffer_head])
                else:
                    # Buffer bị wrap, cần nối 2 phần
                    audio_data = bytes(circular_buffer[buffer_tail:]) + bytes(circular_buffer[:buffer_head])
                
                print(f"🎵 Xử lý audio: {len(audio_data)} bytes, silence: {silence_duration:.1f}s")
                print(f"📊 Buffer info: Tail={buffer_tail}, Head={buffer_head}, Size={len(audio_data)}")
                
                # Debug: Kiểm tra audio quality
                if len(audio_data) >= 2:
                    samples = struct.unpack(f"<{len(audio_data)//2}h", audio_data)
                    rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
                    max_amplitude = max(abs(s) for s in samples)
                    duration_seconds = len(samples) / 16000.0
                    print(f"📊 Audio stats: RMS={rms:.1f}, Max={max_amplitude}, Samples={len(samples)}, Duration={duration_seconds:.2f}s")
                    
                    # Chỉ xử lý nếu audio đủ mạnh
                    if rms > MIN_SPEECH_RMS or max_amplitude > 2000:
                        # Áp dụng audio preprocessing
                        if ENABLE_PREPROCESSING:
                            processed_buffer = audio_preprocessing(audio_data)
                            print(f"🔧 Audio preprocessing applied")
                        else:
                            processed_buffer = audio_data
                        
                        # Lưu audio thành WAV file
                        wav_file = save_audio_to_wav(processed_buffer)
                        if wav_file:
                            try:
                                # Sử dụng Google Speech Recognition để nhận dạng
                                transcription = transcribe_with_google_speech(wav_file)
                                
                                if transcription:
                                    # Gửi kết quả cuối cùng
                                    socketio.emit("final", {
                                        "text": transcription,
                                        "timestamp": timestamp,
                                        "seq": seq
                                    })
                                    print(f"🎯 Final (Google Speech): {transcription}")
                                    # Reset recording state
                                    is_recording = False
                                    consecutive_silence_count = 0
                                else:
                                    print(f"🔇 Google Speech không nhận dạng được text")
                                    # Reset recording state
                                    is_recording = False
                                    consecutive_silence_count = 0
                                    
                            finally:
                                # Xóa file WAV tạm thời
                                try:
                                    os.unlink(wav_file)
                                except:
                                    pass
                        else:
                            print(f"❌ Không thể tạo WAV file")
                            is_recording = False
                            consecutive_silence_count = 0
                    else:
                        print(f"🔇 Audio quá yếu (RMS={rms:.1f}), bỏ qua")
                        is_recording = False
                        consecutive_silence_count = 0
                else:
                    print(f"🔇 Audio data quá ngắn: {len(audio_data)} bytes")
                    is_recording = False
                    consecutive_silence_count = 0
                
        except Exception as e:
            print(f"❌ Lỗi ASR worker: {e}")
            is_recording = False
            consecutive_silence_count = 0
            continue

def create_templates():
    """Tạo thư mục templates và file HTML nếu chưa có"""
    os.makedirs("templates", exist_ok=True)
    
    html_content = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎙️ Live Speech Recognition (Circular Buffer)</title>
    <script src="https://cdn.socket.io/4.7.4/socket.io.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .status {
            text-align: center;
            margin-bottom: 20px;
            padding: 10px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.2);
        }
        
        .transcript-container {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            min-height: 300px;
        }
        
        #partial {
            color: #ffd700;
            font-style: italic;
            font-size: 1.2em;
            margin-bottom: 15px;
            padding: 10px;
            background: rgba(255, 215, 0, 0.1);
            border-radius: 8px;
            border-left: 4px solid #ffd700;
        }
        
        #final {
            line-height: 1.6;
            font-size: 1.1em;
        }
        
        .word {
            display: inline-block;
            margin: 2px 4px;
            padding: 4px 8px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            transition: all 0.3s ease;
        }
        
        .word:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .stat-item {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #ffd700;
        }
        
        .stat-label {
            font-size: 0.9em;
            opacity: 0.8;
        }
        
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .connected {
            background: #4CAF50;
            color: white;
        }
        
        .disconnected {
            background: #f44336;
            color: white;
        }
        
        .model-info {
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid #4CAF50;
            border-radius: 8px;
            padding: 10px;
            margin: 10px 0;
            text-align: center;
        }
        
        .performance-info {
            background: rgba(0, 150, 255, 0.1);
            border: 1px solid #0096FF;
            border-radius: 8px;
            padding: 10px;
            margin: 10px 0;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ Live Speech Recognition</h1>
        
        <div class="model-info">
            <strong>🤖 Engine:</strong> Google Speech Recognition + Circular Buffer - Không bị cụt câu
        </div>
        
        <div class="performance-info">
            <strong>⚡ Features:</strong> Lookback 1s, 4s buffer, Real-time processing
        </div>
        
        <div class="status">
            <div id="connection-status" class="connection-status disconnected">
                🔴 Đang kết nối...
            </div>
        </div>
        
        <div class="transcript-container">
            <h3>📝 Transcript Real-time:</h3>
            <div id="partial"></div>
            <div id="final"></div>
        </div>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-value" id="packets-received">0</div>
                <div class="stat-label">Packets nhận</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="final-count">0</div>
                <div class="stat-label">Final results</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="speech-engine">Circular Buffer</div>
                <div class="stat-label">Engine</div>
            </div>
        </div>
    </div>

    <script>
        var socket = io();
        var finalCount = 0;
        var packetsReceived = 0;

        // Kết nối Socket.IO
        socket.on("connect", function() {
            document.getElementById("connection-status").className = "connection-status connected";
            document.getElementById("connection-status").innerHTML = "🟢 Đã kết nối";
        });

        socket.on("disconnect", function() {
            document.getElementById("connection-status").className = "connection-status disconnected";
            document.getElementById("connection-status").innerHTML = "🔴 Mất kết nối";
        });

        // Nhận final results từ Google Speech
        socket.on("final", function(msg) {
            finalCount++;
            let div = document.getElementById("final");
            let timestamp = new Date(msg.timestamp).toLocaleTimeString();
            
            div.innerHTML += `<div class="word">${msg.text}</div>`;
            document.getElementById("partial").innerHTML = "";
            document.getElementById("final-count").innerText = finalCount;
            
            // Auto-scroll xuống dưới
            div.scrollTop = div.scrollHeight;
        });

        // Cập nhật stats
        setInterval(function() {
            // Có thể thêm cập nhật stats real-time ở đây
        }, 1000);
    </script>
</body>
</html>"""
    
    with open("templates/index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("✅ Templates đã được tạo")

def check_dependencies():
    """Kiểm tra dependencies cần thiết"""
    try:
        import speech_recognition
        print("✅ SpeechRecognition đã được cài đặt")
        return True
    except ImportError:
        print("❌ SpeechRecognition chưa được cài đặt")
        print("📦 Cài đặt: pip install SpeechRecognition")
        return False

if __name__ == "__main__":
    print("🚀 Khởi động ESP32 + INMP441 Real-time Streaming Server với Circular Buffer...")
    print(f"📡 Flask server: http://localhost:{FLASK_PORT}")
    print(f"🎧 UDP server: {HOST}:{UDP_PORT}")
    print(f"🌐 Speech engine: Google Speech Recognition + Circular Buffer")
    print(f"📊 Buffer: {CIRCULAR_BUFFER_SIZE//1000}KB, Lookback: {LOOKBACK_SIZE//1000}KB")
    print("=" * 50)
    
    # Kiểm tra dependencies
    if not check_dependencies():
        print("❌ Thiếu dependencies, vui lòng cài đặt trước")
        exit(1)
    
    # Tạo templates
    create_templates()
    
    # Khởi động các threads
    udp_thread = threading.Thread(target=udp_listener, daemon=True)
    asr_thread = threading.Thread(target=asr_worker, daemon=True)
    
    print("🔄 Đang khởi động UDP Listener thread...")
    udp_thread.start()
    print("✅ UDP Listener thread đã khởi động")
    
    print("🔄 Đang khởi động ASR Worker thread...")
    asr_thread.start()
    print("✅ ASR Worker thread đã khởi động với Circular Buffer")
    
    # Kiểm tra thread có alive không
    time.sleep(2)
    if asr_thread.is_alive():
        print("✅ ASR Worker thread đang chạy bình thường")
    else:
        print("❌ ASR Worker thread đã dừng!")
    
    # Chạy Flask-SocketIO server
    print("🚀 Khởi động Flask-SocketIO server...")
    socketio.run(app, host="0.0.0.0", port=FLASK_PORT, debug=False) 