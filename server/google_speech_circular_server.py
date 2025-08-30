#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Speech Circular Server - Real-time speech recognition với ESP32 + INMP441
Sử dụng circular buffer để tránh cắt câu và Google Speech API
"""

import socket
import struct
import threading
import time
import os
import tempfile
import wave
import signal
import sys
from collections import deque
import numpy as np
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# Import từ audio_utils package
from audio_utils import (
    audio_preprocessing_improved,
    transcribe_audio_with_google,
    check_audio_dependencies,
    TranscriptLogger
)

# ====== UDP CONFIG ======
HOST = "0.0.0.0"
UDP_PORT = 5005
FLASK_PORT = 5000
q_audio = deque(maxlen=1000) # Changed from queue.Queue() to deque(maxlen=1000)

# Global flag để dừng threads
shutdown_event = threading.Event()

def signal_handler(signum, frame):
    """Signal handler để graceful shutdown"""
    print(f"\n🛑 Nhận signal {signum}, đang dừng server...")
    shutdown_event.set()
    time.sleep(2)  # Đợi threads dừng
    print("✅ Server đã dừng an toàn")
    sys.exit(0)

# Đăng ký signal handlers
signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

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
MIN_SILENCE_DURATION = 0.5    # Giảm từ 1.0s xuống 0.5s
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
        "audio_queue_size": len(q_audio)
    }

@app.route('/test')
def test():
    """Test kết nối"""
    return {"message": "Server hoạt động bình thường", "timestamp": time.time()}

@app.route('/transcript-stats')
def transcript_stats():
    """API thống kê transcript log"""
    try:
        stats = transcript_logger.get_stats()
        return {
            "transcript_log": {
                "filepath": transcript_logger.get_filepath(),
                "stats": stats
            }
        }
    except Exception as e:
        return {"error": str(e)}

def save_audio_to_wav(audio_data, sample_rate=16000):
    """Lưu audio data thành file WAV tạm thời"""
    try:
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

def udp_listener():
    """Thread lắng nghe UDP audio từ ESP32"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, UDP_PORT))
    print(f"🎧 UDP Audio server đang lắng nghe trên {HOST}:{UDP_PORT}")
    print(f"📡 Đang chờ audio packets từ ESP32...")
    
    packet_count = 0
    
    while not shutdown_event.is_set():
        try:
            # Set timeout để có thể kiểm tra shutdown event
            sock.settimeout(1.0)
            data, addr = sock.recvfrom(2048)
            packet_count += 1
            
            if packet_count % 500 == 0:  # Log mỗi 500 packets
                print(f"📦 Nhận {packet_count} packets từ {addr}")
            
            if len(data) <= 12: 
                continue
                
            # Parse header ESP32: seq(4) + time_ms(4) + codec(1) + len24(3)
            try:
                seq, time_ms, codec, len_b2, len_b1, len_b0 = struct.unpack_from("<IIBBBB", data, 0)
                length = (len_b2 << 16) | (len_b1 << 8) | len_b0
                payload = data[12:12+length]
                
                if len(payload) == length:
                    q_audio.append((payload, time_ms, seq))
                    
            except struct.error as e:
                # Nếu không parse được header, coi như raw audio
                q_audio.append((data, int(time.time() * 1000), 0))
                
        except socket.timeout:
            # Timeout, kiểm tra shutdown event
            continue
        except Exception as e:
            if not shutdown_event.is_set():
                print(f"❌ Lỗi UDP listener: {e}")
            continue
    
    print("🛑 UDP Listener đã dừng")
    sock.close()

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
    
    # Adaptive threshold để cải thiện speech detection
    adaptive_rms_threshold = MIN_SPEECH_RMS
    recent_rms_values = []
    max_recent_rms = 1000  # Giá trị tối đa để tránh quá nhạy
    
    # Thêm tracking để tránh spam API calls
    last_api_call_time = 0.0  # Thời gian gọi API cuối cùng
    
    processed_chunks = 0
    empty_queue_count = 0  # Counter để tránh spam log
    
    while not shutdown_event.is_set():
        try:
            # Kiểm tra queue có data không trước khi pop
            if len(q_audio) == 0:
                empty_queue_count += 1
                if empty_queue_count % 1000 == 0:  # Log mỗi 1000 lần queue trống
                    print(f"⏳ ASR Worker: Queue trống, đang chờ audio data... (count: {empty_queue_count})")
                time.sleep(0.01)  # Sleep 10ms nếu queue trống
                continue
            
            # Reset counter khi có data
            empty_queue_count = 0
            chunk, timestamp, seq = q_audio.popleft()
            processed_chunks += 1
            
            # Debug logging mỗi 100 chunks
            if processed_chunks % 100 == 0:
                print(f"🔄 ASR Worker: Đã xử lý {processed_chunks} chunks")
            
            # Kiểm tra tiếng ồn (silence detection) với circular buffer
            if len(chunk) >= 2:
                samples = struct.unpack(f"<{len(chunk)//2}h", chunk)
                rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
                max_amp = max(abs(s) for s in samples)
                
                # Cập nhật adaptive threshold
                recent_rms_values.append(rms)
                if len(recent_rms_values) > 100:  # Giữ 100 giá trị gần nhất
                    recent_rms_values.pop(0)
                
                # Tính threshold động dựa trên background noise
                if len(recent_rms_values) > 20:
                    background_rms = np.mean(sorted(recent_rms_values)[:20])  # 20 giá trị thấp nhất
                    adaptive_rms_threshold = max(MIN_SPEECH_RMS * 0.5, background_rms * 2)
                    adaptive_rms_threshold = min(adaptive_rms_threshold, max_recent_rms)
                
                # Cải thiện logic phát hiện speech - thêm ngưỡng silence
                is_speech = (
                    rms > adaptive_rms_threshold or 
                    max_amp > MIN_AMPLITUDE_THRESHOLD or
                    any(abs(s) > 800 for s in samples) or  # Có ít nhất 1 sample mạnh
                    rms > (MIN_SPEECH_RMS * 0.5)  # Giảm ngưỡng RMS
                )
                
                # Cải thiện silence detection - thêm điều kiện rõ ràng
                is_silence = (
                    rms < SILENCE_RMS_THRESHOLD and 
                    max_amp < SILENCE_AMPLITUDE_THRESHOLD and
                    not any(abs(s) > 800 for s in samples)  # Không có sample mạnh nào
                )
                
                # Debug logging tạm thời để diagnose
                if processed_chunks % 50 == 0:  # Log mỗi 50 chunks
                    print(f"🔍 Debug: RMS={rms:.0f}, Max={max_amp}, Speech={is_speech}, Silence={is_silence}, Threshold={adaptive_rms_threshold:.0f}")
                    print(f"🔍 Silence counters: consecutive={consecutive_silence_count}, duration={consecutive_silence_count * 0.02:.2f}s")
                
                if is_speech:
                    # Chỉ log khi bắt đầu record mới
                    if not is_recording:
                        print(f"🎤 Bắt đầu record: RMS={rms:.0f}")
                    
                    # Reset silence counter khi có speech
                    if consecutive_silence_count > 0:
                        print(f"🔇 Reset silence: {consecutive_silence_count} → 0")
                    consecutive_silence_count = 0
                    
                    # Thêm chunk vào circular buffer
                    chunk_size = len(chunk)
                    for i in range(chunk_size):
                        circular_buffer[buffer_head] = chunk[i]
                        buffer_head = (buffer_head + 1) % CIRCULAR_BUFFER_SIZE
                    
                    if not is_recording:
                        # Bắt đầu record, lùi lại LOOKBACK_SIZE
                        buffer_tail = (buffer_head - LOOKBACK_SIZE) % CIRCULAR_BUFFER_SIZE
                        if buffer_tail < 0:
                            buffer_tail = 0
                        is_recording = True
                    else:
                        # Đang record, cập nhật tail nếu cần để lấy câu dài hơn
                        current_tail = (buffer_head - LOOKBACK_SIZE) % CIRCULAR_BUFFER_SIZE
                        if current_tail < 0:
                            current_tail = 0
                        # Chỉ cập nhật tail nếu nó gần head hơn (để lấy câu dài)
                        if (buffer_head - current_tail) % CIRCULAR_BUFFER_SIZE > (buffer_head - buffer_tail) % CIRCULAR_BUFFER_SIZE:
                            buffer_tail = current_tail
                        
                        # Log recording duration mỗi 100 chunks
                        if processed_chunks % 100 == 0:
                            buffer_size = (buffer_head - buffer_tail) % CIRCULAR_BUFFER_SIZE
                            recording_duration = buffer_size / 32000.0
                            print(f"🎤 Đang record: {recording_duration:.1f}s / {MAX_RECORDING_DURATION}s")
                elif is_silence:
                    # CÓ silence rõ ràng - tăng silence counter
                    consecutive_silence_count += 1
                    silence_duration = consecutive_silence_count * 0.02  # 20ms per chunk
                    
                    # Debug silence detection
                    if consecutive_silence_count % 5 == 0:  # Log mỗi 5 lần silence
                        print(f"🔇 Silence: {consecutive_silence_count} consecutive, RMS={rms:.0f}, Duration={silence_duration:.2f}s")
                    
                    # Thêm chunk vào circular buffer ngay cả khi silence
                    chunk_size = len(chunk)
                    for i in range(chunk_size):
                        circular_buffer[buffer_head] = chunk[i]
                        buffer_head = (buffer_head + 1) % CIRCULAR_BUFFER_SIZE
                    
                    # Nếu silence đủ lâu và đang record, đánh dấu để xử lý
                    if silence_duration >= MIN_SILENCE_DURATION and is_recording:
                        print(f"🔇 Silence đủ lâu ({silence_duration:.1f}s), chuẩn bị xử lý...")
                        # Không continue, để tiếp tục xử lý ở phần dưới
                    
                    # Chỉ continue nếu chưa đủ silence
                    if silence_duration < MIN_SILENCE_DURATION:
                        continue
                else:
                    # Trường hợp không rõ ràng - vẫn tăng silence counter nhẹ
                    consecutive_silence_count += 1
                    silence_duration = consecutive_silence_count * 0.02
                    
                    # Debug ambiguous case
                    if consecutive_silence_count % 10 == 0:
                        print(f"🔇 Ambiguous: {consecutive_silence_count} consecutive, RMS={rms:.0f}, Duration={silence_duration:.2f}s")
                    
                    # Thêm chunk vào circular buffer
                    chunk_size = len(chunk)
                    for i in range(chunk_size):
                        circular_buffer[buffer_head] = chunk[i]
                        buffer_head = (buffer_head + 1) % CIRCULAR_BUFFER_SIZE
                    
                    if silence_duration >= MIN_SILENCE_DURATION and is_recording:
                        print(f"🔇 Ambiguous silence đủ lâu ({silence_duration:.1f}s), chuẩn bị xử lý...")
                    elif silence_duration < MIN_SILENCE_DURATION:
                        continue
                        
            # Xử lý khi có silence đủ lâu và đang record HOẶC đạt max duration
            silence_duration = consecutive_silence_count * 0.02  # 20ms per chunk
            
            # Tính thời gian recording hiện tại
            if is_recording:
                # Tính buffer size hiện tại
                if buffer_head >= buffer_tail:
                    buffer_size = buffer_head - buffer_tail
                else:
                    buffer_size = (CIRCULAR_BUFFER_SIZE - buffer_tail) + buffer_head
                
                # Chuyển bytes thành thời gian (16-bit samples, 16kHz)
                current_recording_duration = buffer_size / 32000.0  # 32000 bytes = 1 giây
            else:
                current_recording_duration = 0.0
            
            # Điều kiện xử lý: silence đủ lâu HOẶC đạt max duration
            should_process = (
                is_recording and (
                    silence_duration >= MIN_SILENCE_DURATION or  # Silence đủ lâu
                    current_recording_duration >= MAX_RECORDING_DURATION  # Đạt max duration
                )
            )
            
            # Thêm kiểm tra delay để tránh spam API calls
            current_time = time.time()
            time_since_last_api = current_time - last_api_call_time
            if time_since_last_api < MIN_API_CALL_DELAY:
                should_process = False
            
            # Debug processing conditions
            if processed_chunks % 50 == 0:
                print(f"🔍 Processing check: recording={is_recording}, silence={silence_duration:.2f}s, duration={current_recording_duration:.2f}s, should_process={should_process}")
                if not should_process and time_since_last_api < MIN_API_CALL_DELAY:
                    print(f"⏰ API delay: {time_since_last_api:.1f}s < {MIN_API_CALL_DELAY}s")
            
            if should_process:
                if silence_duration >= MIN_SILENCE_DURATION:
                    print(f"🎯 BẮT ĐẦU XỬ LÝ AUDIO: silence={silence_duration:.1f}s")
                else:
                    print(f"🎯 BẮT ĐẦU XỬ LÝ AUDIO: đạt max duration={current_recording_duration:.1f}s")
                
                # Cập nhật thời gian gọi API
                last_api_call_time = current_time
                
                # Trích xuất audio từ circular buffer (từ tail đến head)
                if buffer_head >= buffer_tail:
                    # Buffer không bị wrap
                    audio_data = bytes(circular_buffer[buffer_tail:buffer_head])
                else:
                    # Buffer bị wrap, cần nối 2 phần
                    audio_data = bytes(circular_buffer[buffer_tail:]) + bytes(circular_buffer[:buffer_head])
                
                print(f"🎵 Audio: {len(audio_data)} bytes, duration: {len(audio_data)//32000:.1f}s")
                
                # Debug: Kiểm tra audio quality
                if len(audio_data) >= 2:
                    samples = struct.unpack(f"<{len(audio_data)//2}h", audio_data)
                    rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
                    max_amplitude = max(abs(s) for s in samples)
                    duration_seconds = len(samples) / 16000.0
                    
                    # Cải thiện điều kiện xử lý audio - nhạy hơn
                    should_process_audio = (
                        rms > (MIN_SPEECH_RMS * 0.5) or  # Giảm ngưỡng RMS
                        max_amplitude > (MIN_AMPLITUDE_THRESHOLD * 0.5) or  # Giảm ngưỡng amplitude
                        any(abs(s) > 600 for s in samples) or  # Có ít nhất 1 sample mạnh
                        duration_seconds > 0.5  # Audio đủ dài (ít nhất 0.5s)
                    )
                    
                    if should_process_audio:
                        print(f"✅ Audio đủ chất lượng để xử lý")
                        
                        # Áp dụng audio preprocessing
                        if ENABLE_PREPROCESSING:
                            processed_buffer = audio_preprocessing_improved(audio_data) # Changed from audio_preprocessing to audio_preprocessing_improved
                        
                        # Lưu audio thành WAV file
                        wav_file = save_audio_to_wav(processed_buffer)
                        if wav_file:
                            try:
                                # Sử dụng Google Speech Recognition để nhận dạng
                                print(f"🔄 Đang gửi lên Google Speech API...")
                                transcription = transcribe_audio_with_google(wav_file, GOOGLE_SPEECH_LANGUAGE)
                                
                                if transcription:
                                    # Ghi transcript ra file log
                                    transcript_logger.log_transcript_simple(transcription)
                                    
                                    # Gửi kết quả cuối cùng
                                    socketio.emit("final", {
                                        "text": transcription,
                                        "timestamp": timestamp,
                                        "seq": seq
                                    })
                                    print(f"🎯 Final (Google Speech): {transcription}")
                                    
                                    # XÓA BUFFER sau khi xử lý thành công để tránh lặp lại
                                    print("🧹 Đang xóa buffer để tránh duplicate...")
                                    circular_buffer = bytearray(CIRCULAR_BUFFER_SIZE)
                                    buffer_head = 0
                                    buffer_tail = 0
                                    
                                    # Reset recording state
                                    is_recording = False
                                    consecutive_silence_count = 0
                                else:
                                    print(f"🔇 Google Speech không nhận dạng được text")
                                    
                                    # XÓA BUFFER ngay cả khi không nhận diện được để tránh lặp lại
                                    print("🧹 Đang xóa buffer (không nhận diện được)...")
                                    circular_buffer = bytearray(CIRCULAR_BUFFER_SIZE)
                                    buffer_head = 0
                                    buffer_tail = 0
                                    
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
                            
                            # XÓA BUFFER khi không thể tạo WAV file
                            print("🧹 Đang xóa buffer (không thể tạo WAV)...")
                            circular_buffer = bytearray(CIRCULAR_BUFFER_SIZE)
                            buffer_head = 0
                            buffer_tail = 0
                            
                            is_recording = False
                            consecutive_silence_count = 0
                    else:
                        print(f"🔇 Audio không đủ chất lượng")
                        
                        # XÓA BUFFER khi audio không đủ chất lượng
                        print("🧹 Đang xóa buffer (audio không đủ chất lượng)...")
                        circular_buffer = bytearray(CIRCULAR_BUFFER_SIZE)
                        buffer_head = 0
                        buffer_tail = 0
                        
                        is_recording = False
                        consecutive_silence_count = 0
                else:
                    print(f"🔇 Audio data quá ngắn: {len(audio_data)} bytes")
                    
                    # XÓA BUFFER khi audio quá ngắn
                    print("🧹 Đang xóa buffer (audio quá ngắn)...")
                    circular_buffer = bytearray(CIRCULAR_BUFFER_SIZE)
                    buffer_head = 0
                    buffer_tail = 0
                    
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
    return check_audio_dependencies()

if __name__ == "__main__":
    print("🚀 Khởi động ESP32 + INMP441 Real-time Streaming Server với Circular Buffer...")
    print(f"📡 Flask server: http://localhost:{FLASK_PORT}")
    print(f"🎧 UDP server: {HOST}:{UDP_PORT}")
    print(f"🌐 Speech engine: Google Speech Recognition + Circular Buffer")
    print(f"📊 Buffer: {CIRCULAR_BUFFER_SIZE//1000}KB, Lookback: {LOOKBACK_SIZE//1000}KB")
    print("=" * 50)
    print("🏗️ MODULAR ARCHITECTURE (audio_utils):")
    print(f"   • audio_processing: Improved audio preprocessing")
    print(f"   • speech_recognition: Google Speech API integration")
    print(f"   • dependencies: Library dependency checker")
    print("=" * 50)
    print("🆕 CẢI TIẾN SPEECH DETECTION:")
    print(f"   • MIN_SPEECH_RMS: {MIN_SPEECH_RMS} (giảm từ 500)")
    print(f"   • MIN_SILENCE_DURATION: {MIN_SILENCE_DURATION}s (giảm từ 1.0s)")
    print(f"   • MIN_AMPLITUDE_THRESHOLD: {MIN_AMPLITUDE_THRESHOLD}")
    print(f"   • SILENCE_RMS_THRESHOLD: {SILENCE_RMS_THRESHOLD}")
    print(f"   • SILENCE_AMPLITUDE_THRESHOLD: {SILENCE_AMPLITUDE_THRESHOLD}")
    print(f"   • MAX_RECORDING_DURATION: {MAX_RECORDING_DURATION}s (gửi ngay khi đạt max)")
    print(f"   • MIN_API_CALL_DELAY: {MIN_API_CALL_DELAY}s (delay giữa các lần gọi API)")
    print(f"   • Adaptive threshold: Tự động điều chỉnh dựa trên background noise")
    print(f"   • Enhanced preprocessing: Noise gate + Speech boost")
    print(f"   • Multiple detection conditions: RMS + Amplitude + Sample strength")
    print(f"   • Improved silence detection: Rõ ràng phân biệt speech/silence")
    print(f"   • Auto-send: Gửi ngay khi đạt {MAX_RECORDING_DURATION}s hoặc silence {MIN_SILENCE_DURATION}s")
    print(f"   • Anti-spam: Delay {MIN_API_CALL_DELAY}s giữa các lần gọi API")
    print("=" * 50)
    print("🔧 STABILITY IMPROVEMENTS:")
    print(f"   • Queue empty protection: Kiểm tra trước khi pop")
    print(f"   • Graceful shutdown: Signal handlers + shutdown events")
    print(f"   • Thread safety: Timeout + shutdown checks")
    print(f"   • Error handling: Spam log prevention")
    print("=" * 50)
    print("📝 TRANSCRIPT LOGGING:")
    print(f"   • Auto-save: Mỗi lần detect được chữ sẽ ghi ra file")
    print(f"   • Simple format: Chỉ text, không có log phức tạp")
    print(f"   • File location: transcripts/live_transcript.txt")
    print(f"   • API endpoint: /transcript-stats để xem thống kê")
    print("=" * 50)
    print("🧹 BUFFER MANAGEMENT:")
    print(f"   • Auto-clear: Xóa buffer sau mỗi lần xử lý API")
    print(f"   • Prevent duplicate: Tránh lặp lại audio đã xử lý")
    print(f"   • Fresh start: Mỗi lần xử lý bắt đầu với buffer trống")
    print(f"   • All cases: Xóa buffer cho mọi trường hợp (success/fail)")
    print("=" * 50)
    
    # Kiểm tra dependencies
    if not check_dependencies():
        print("❌ Thiếu dependencies, vui lòng cài đặt trước")
        exit(1)
    
    # Khởi tạo TranscriptLogger
    transcript_logger = TranscriptLogger(output_dir="transcripts", filename="live_transcript.txt")
    print(f"📝 Transcript Logger: {transcript_logger.get_filepath()}")
    
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
    try:
        socketio.run(app, host="0.0.0.0", port=FLASK_PORT, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 Nhận Ctrl+C, đang dừng server...")
        shutdown_event.set()
        time.sleep(2)
        print("✅ Server đã dừng an toàn")
    except Exception as e:
        print(f"❌ Lỗi Flask server: {e}")
        shutdown_event.set()
        time.sleep(2)
        print("✅ Server đã dừng an toàn") 