#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio Test Recorder - Ghi âm test và lưu WAV để kiểm tra chất lượng
Sử dụng để diagnose vấn đề Google Speech Recognition
"""

import socket
import struct
import threading
import time
import os
from datetime import datetime

# Import từ audio_utils package
from audio_utils import (
    audio_preprocessing_improved,
    transcribe_audio_with_google,
    save_audio_to_wav,
    save_transcription_to_txt,
    check_audio_dependencies,
    get_installation_commands
)

# ====== CONFIG ======
HOST = "0.0.0.0"
UDP_PORT = 5005
RECORDING_DURATION = 10.0  # Ghi âm 10 giây
OUTPUT_DIR = "test_recordings"  # Thư mục lưu file test
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit

# ====== NOISE REDUCTION CONFIG ======
# Có thể điều chỉnh các thông số này để test
NOISE_REDUCTION_LEVEL = "medium"  # "light", "medium", "strong" - Đổi từ "strong" sang "medium"
ENABLE_NOTCH_FILTER = True        # Bật/tắt notch filter
ENABLE_SMOOTHING = True           # Bật/tắt smoothing filter
ENABLE_FINAL_NOISE_REDUCTION = False  # Tắt final noise reduction để giữ giọng người

# ====== PRESET CONFIG ======
# Các preset để test nhanh
PRESET = "voice_preserve"  # "voice_preserve", "noise_reduction", "original"

# Preset: Voice Preserve - Giữ giọng người, giảm noise vừa phải
if PRESET == "voice_preserve":
    NOISE_REDUCTION_LEVEL = "light"
    ENABLE_NOTCH_FILTER = True
    ENABLE_SMOOTHING = True
    ENABLE_FINAL_NOISE_REDUCTION = False
# Preset: Noise Reduction - Giảm noise mạnh, có thể mất giọng người
elif PRESET == "noise_reduction":
    NOISE_REDUCTION_LEVEL = "strong"
    ENABLE_NOTCH_FILTER = True
    ENABLE_SMOOTHING = True
    ENABLE_FINAL_NOISE_REDUCTION = True
# Preset: Original - Ít xử lý, giữ nguyên audio
elif PRESET == "original":
    NOISE_REDUCTION_LEVEL = "light"
    ENABLE_NOTCH_FILTER = False
    ENABLE_SMOOTHING = False
    ENABLE_FINAL_NOISE_REDUCTION = False

def udp_audio_recorder():
    """Ghi âm audio từ ESP32 qua UDP"""
    print(f"🎧 UDP Audio Recorder đang lắng nghe trên {HOST}:{UDP_PORT}")
    print(f"⏱️ Sẽ ghi âm {RECORDING_DURATION} giây khi phát hiện speech")
    print(f"📁 Lưu vào thư mục: {OUTPUT_DIR}")
    print("=" * 50)
    
    # Tạo thư mục output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, UDP_PORT))
    
    # Audio buffer
    audio_buffer = bytearray()
    is_recording = False
    recording_start_time = 0
    packet_count = 0
    
    print("🎤 Sẵn sàng ghi âm! Nói gì đó để bắt đầu...")
    
    try:
        while True:
            data, addr = sock.recvfrom(2048)
            packet_count += 1
            
            if packet_count % 100 == 0:
                print(f"📦 Nhận {packet_count} packets...")
            
            if len(data) <= 12:
                continue
            
            # Parse header ESP32
            try:
                seq, time_ms, codec, len_b2, len_b1, len_b0 = struct.unpack_from("<IIBBBB", data, 0)
                length = (len_b2 << 16) | (len_b1 << 8) | len_b0
                payload = data[12:12+length]
                
                if len(payload) == length:
                    # Kiểm tra speech detection
                    if len(payload) >= 2:
                        samples = struct.unpack(f"<{len(payload)//2}h", payload)
                        rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
                        max_amp = max(abs(s) for s in samples)
                        
                        # Speech detection threshold - Tối ưu cho INMP441
                        is_speech = (
                            rms > 150 or  # Giảm từ 200 xuống 150
                            max_amp > 800 or  # Giảm từ 1000 xuống 800
                            any(abs(s) > 600 for s in samples) or  # Giảm từ 800 xuống 600
                            # Thêm điều kiện mới: có ít nhất 20% samples mạnh
                            sum(1 for s in samples if abs(s) > 500) > len(samples) * 0.2
                        )
                        
                        if is_speech and not is_recording:
                            # Bắt đầu ghi âm
                            is_recording = True
                            recording_start_time = time.time()
                            audio_buffer.clear()
                            print(f"🎤 Bắt đầu ghi âm! RMS={rms:.0f}, Max={max_amp}")
                        
                        if is_recording:
                            # Thêm audio vào buffer
                            audio_buffer.extend(payload)
                            
                            # Kiểm tra thời gian ghi âm
                            elapsed_time = time.time() - recording_start_time
                            if elapsed_time >= RECORDING_DURATION:
                                # Kết thúc ghi âm
                                is_recording = False
                                
                                # Tạo filename với timestamp và thông tin audio
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                rms_str = f"rms{int(rms)}"
                                max_str = f"max{int(max_amp)}"
                                filename = f"test_recording_{timestamp}_{rms_str}_{max_str}.wav"
                                
                                print(f"⏹️ Kết thúc ghi âm: {elapsed_time:.1f}s")
                                print(f"📊 Buffer size: {len(audio_buffer)} bytes")
                                print(f"📊 Final audio stats: RMS={rms:.0f}, Max={max_amp}")
                                
                                # Lưu raw audio
                                raw_filename = f"raw_{filename}"
                                raw_audio_data = bytes(audio_buffer)
                                save_audio_to_wav(raw_audio_data, raw_filename)
                                
                                # Lưu processed audio
                                processed_audio_data = audio_preprocessing_improved(raw_audio_data)
                                processed_filename = f"processed_{filename}"
                                save_audio_to_wav(processed_audio_data, processed_filename)
                                
                                print(f"✅ Đã lưu 2 files:")
                                print(f"   • Raw: {raw_filename}")
                                print(f"   • Processed: {processed_filename}")
                                
                                # ===== SPEECH RECOGNITION =====
                                print("🎤 Bắt đầu nhận dạng giọng nói...")
                                
                                # Test với raw audio trước
                                print(f"🔍 Testing với raw audio...")
                                raw_transcription = transcribe_audio_with_google(
                                    os.path.join(OUTPUT_DIR, raw_filename)
                                )
                                
                                # Lưu kết quả raw audio
                                save_transcription_to_txt(
                                    raw_transcription, 
                                    raw_filename, 
                                    OUTPUT_DIR
                                )
                                
                                # Test với processed audio
                                print(f"🔍 Testing với processed audio...")
                                processed_transcription = transcribe_audio_with_google(
                                    os.path.join(OUTPUT_DIR, processed_filename)
                                )
                                
                                # Lưu kết quả processed audio
                                save_transcription_to_txt(
                                    processed_transcription, 
                                    processed_filename, 
                                    OUTPUT_DIR
                                )
                                
                                # So sánh kết quả
                                print("📊 KẾT QUẢ SO SÁNH:")
                                print(f"   • Raw audio: {'✅' if raw_transcription else '❌'} {raw_transcription[:50] if raw_transcription else 'Không nhận dạng được'}")
                                print(f"   • Processed audio: {'✅' if processed_transcription else '❌'} {processed_transcription[:50] if processed_transcription else 'Không nhận dạng được'}")
                                
                                if raw_transcription and processed_transcription:
                                    if raw_transcription == processed_transcription:
                                        print("🎯 Kết quả giống nhau - Audio processing không ảnh hưởng đến nhận dạng")
                                    else:
                                        print("🔄 Kết quả khác nhau - Audio processing có ảnh hưởng đến nhận dạng")
                                elif raw_transcription and not processed_transcription:
                                    print("⚠️ Raw audio nhận dạng được nhưng processed audio không - Audio processing có thể quá aggressive")
                                elif not raw_transcription and processed_transcription:
                                    print("🎉 Processed audio nhận dạng được nhưng raw audio không - Audio processing cải thiện chất lượng!")
                                else:
                                    print("❌ Cả hai đều không nhận dạng được - Cần kiểm tra audio quality")
                                
                                print("=" * 50)
                                print("🎤 Sẵn sàng ghi âm tiếp theo! Nói gì đó...")
                                
                                # Reset buffer
                                audio_buffer.clear()
                        
            except struct.error as e:
                # Nếu không parse được header, coi như raw audio
                if is_recording:
                    audio_buffer.extend(data)
                    
    except KeyboardInterrupt:
        print("\n⏹️ Dừng ghi âm...")
        sock.close()
        print("✅ Đã dừng UDP Audio Recorder")

if __name__ == "__main__":
    print("🚀 Audio Test Recorder - Ghi âm test để diagnose Google Speech")
    print(f"📡 UDP Port: {UDP_PORT}")
    print(f"⏱️ Recording Duration: {RECORDING_DURATION}s")
    print(f"📁 Output Directory: {OUTPUT_DIR}")
    print("=" * 50)
    print("🔧 IMPROVED AUDIO PREPROCESSING:")
    print(f"   • Band-pass filter: 80Hz - 7.5kHz (Butterworth, order=4)")
    print(f"   • Professional noise reduction: noisereduce library")
    print(f"   • Audio normalization: 95% max volume")
    print(f"   • Sample rate: {SAMPLE_RATE}Hz")
    print("=" * 50)
    print("🎤 SPEECH RECOGNITION FEATURES:")
    print(f"   • Google Speech API integration")
    print(f"   • Test both raw and processed audio")
    print(f"   • Save results to TXT files")
    print(f"   • Compare recognition accuracy")
    print(f"   • Language: Vietnamese (vi-VN)")
    print("=" * 50)
    print("📚 Required libraries:")
    print(f"   • noisereduce: Professional noise reduction")
    print(f"   • scipy.signal: High-quality Butterworth filters")
    print(f"   • numpy: Audio processing")
    print(f"   • speech_recognition: Google Speech API")
    print("=" * 50)
    print("🏗️ MODULAR ARCHITECTURE:")
    print(f"   • audio_processing: Audio preprocessing functions")
    print(f"   • speech_recognition: Google Speech API integration")
    print(f"   • file_utils: WAV and TXT file handling")
    print(f"   • dependencies: Library dependency checker")
    print("=" * 50)
    
    # Kiểm tra dependencies
    if not check_audio_dependencies():
        print("❌ Thiếu dependencies, vui lòng cài đặt trước")
        print("📦 Các lệnh cài đặt:")
        for cmd in get_installation_commands():
            print(f"   • {cmd}")
        exit(1)
    
    try:
        udp_audio_recorder()
    except KeyboardInterrupt:
        print("\n👋 Tạm biệt!") 