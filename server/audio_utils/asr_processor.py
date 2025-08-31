#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASR Processor - Xử lý ASR với Google Speech Recognition + Circular Buffer
"""

import struct
import time
import tempfile
import wave
import os
import numpy as np

import audio_utils.server_config as config
from .audio_processing import audio_preprocessing_improved
from .speech_recognition import transcribe_audio_with_google
from .wake_word_handler import (
    check_wake_word, process_wake_word_detection, 
    process_question_capture, reset_question_mode
)

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

def asr_worker(socketio):
    """Thread xử lý ASR với Google Speech Recognition + Circular Buffer"""
    
    print("🎤 ASR Worker đã sẵn sàng xử lý audio với Google Speech Recognition + Circular Buffer...")
    print(f"📊 Cấu hình: circular_buffer_size={config.CIRCULAR_BUFFER_SIZE}, lookback_size={config.LOOKBACK_SIZE}")
    print(f"🌐 Ngôn ngữ: {config.GOOGLE_SPEECH_LANGUAGE}")
    
    # Circular buffer với lookback
    circular_buffer = bytearray(config.CIRCULAR_BUFFER_SIZE)
    buffer_head = 0  # Vị trí hiện tại trong buffer
    buffer_tail = 0  # Vị trí bắt đầu speech
    is_recording = False  # Trạng thái đang record
    consecutive_silence_count = 0
    
    # Adaptive threshold để cải thiện speech detection
    adaptive_rms_threshold = config.MIN_SPEECH_RMS
    recent_rms_values = []
    max_recent_rms = 1000  # Giá trị tối đa để tránh quá nhạy
    
    # Thêm tracking để tránh spam API calls
    last_api_call_time = 0.0  # Thời gian gọi API cuối cùng
    
    processed_chunks = 0
    empty_queue_count = 0  # Counter để tránh spam log
    
    while not config.shutdown_event.is_set():
        try:
            # Kiểm tra queue có data không trước khi pop
            if len(config.q_audio) == 0:
                empty_queue_count += 1
                if empty_queue_count % 1000 == 0:  # Log mỗi 1000 lần queue trống
                    print(f"⏳ ASR Worker: Queue trống, đang chờ audio data... (count: {empty_queue_count})")
                time.sleep(0.01)  # Sleep 10ms nếu queue trống
                continue
            
            # Reset counter khi có data
            empty_queue_count = 0
            chunk, timestamp, seq = config.q_audio.popleft()
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
                    adaptive_rms_threshold = max(config.MIN_SPEECH_RMS * 0.5, background_rms * 2)
                    adaptive_rms_threshold = min(adaptive_rms_threshold, max_recent_rms)
                
                # Logic phát hiện speech/silence
                is_speech = _detect_speech(rms, max_amp, samples, adaptive_rms_threshold)
                is_silence = _detect_silence(rms, max_amp, samples)
                
                # Xử lý circular buffer
                buffer_head, buffer_tail, is_recording, consecutive_silence_count = _process_audio_chunk(
                    chunk, is_speech, is_silence, circular_buffer, buffer_head, buffer_tail,
                    is_recording, consecutive_silence_count, processed_chunks, rms, max_amp
                )
                
            # Kiểm tra điều kiện xử lý audio
            should_process, current_time = _should_process_audio(
                is_recording, consecutive_silence_count, buffer_head, buffer_tail, last_api_call_time
            )
            
            if should_process:
                # Xử lý audio và nhận dạng
                result = _process_audio_recognition(
                    circular_buffer, buffer_head, buffer_tail, 
                    timestamp, seq, socketio, current_time
                )
                
                if result:
                    last_api_call_time = current_time
                
                # Reset buffer sau khi xử lý
                circular_buffer = bytearray(config.CIRCULAR_BUFFER_SIZE)
                buffer_head = 0
                buffer_tail = 0
                is_recording = False
                consecutive_silence_count = 0
                            
        except Exception as e:
            print(f"❌ Lỗi ASR worker: {e}")
            reset_question_mode()
            is_recording = False
            consecutive_silence_count = 0
            continue

def _detect_speech(rms, max_amp, samples, adaptive_rms_threshold):
    """Phát hiện speech từ audio samples"""
    return (
        rms > adaptive_rms_threshold or 
        max_amp > config.MIN_AMPLITUDE_THRESHOLD or
        any(abs(s) > 800 for s in samples) or  # Có ít nhất 1 sample mạnh
        rms > (config.MIN_SPEECH_RMS * 0.5)  # Giảm ngưỡng RMS
    )

def _detect_silence(rms, max_amp, samples):
    """Phát hiện silence từ audio samples"""
    return (
        rms < config.SILENCE_RMS_THRESHOLD and 
        max_amp < config.SILENCE_AMPLITUDE_THRESHOLD and
        not any(abs(s) > 800 for s in samples)  # Không có sample mạnh nào
    )

def _process_audio_chunk(chunk, is_speech, is_silence, circular_buffer, buffer_head, buffer_tail,
                        is_recording, consecutive_silence_count, processed_chunks, rms, max_amp):
    """Xử lý chunk audio và cập nhật circular buffer"""
    
    if is_speech:
        # Reset silence counter khi có speech
        if consecutive_silence_count > 0:
            print(f"🔇 Reset silence: {consecutive_silence_count} → 0")
        consecutive_silence_count = 0
        
        # Thêm chunk vào circular buffer
        chunk_size = len(chunk)
        for i in range(chunk_size):
            circular_buffer[buffer_head] = chunk[i]
            buffer_head = (buffer_head + 1) % config.CIRCULAR_BUFFER_SIZE
        
        if not is_recording:
            # Bắt đầu record, lùi lại LOOKBACK_SIZE
            buffer_tail = (buffer_head - config.LOOKBACK_SIZE) % config.CIRCULAR_BUFFER_SIZE
            if buffer_tail < 0:
                buffer_tail = 0
            is_recording = True
            print(f"🎤 Bắt đầu record: RMS={rms:.0f}")
        else:
            # Cập nhật tail nếu cần để lấy câu dài hơn
            current_tail = (buffer_head - config.LOOKBACK_SIZE) % config.CIRCULAR_BUFFER_SIZE
            if current_tail < 0:
                current_tail = 0
            # Chỉ cập nhật tail nếu nó gần head hơn
            if (buffer_head - current_tail) % config.CIRCULAR_BUFFER_SIZE > (buffer_head - buffer_tail) % config.CIRCULAR_BUFFER_SIZE:
                buffer_tail = current_tail
                
    elif is_silence:
        # CÓ silence rõ ràng - tăng silence counter
        consecutive_silence_count += 1
        silence_duration = consecutive_silence_count * 0.02  # 20ms per chunk
        
        # Debug silence detection
        if consecutive_silence_count % 5 == 0:
            print(f"🔇 Silence: {consecutive_silence_count} consecutive, RMS={rms:.0f}, Duration={silence_duration:.2f}s")
        
        # Thêm chunk vào circular buffer ngay cả khi silence
        chunk_size = len(chunk)
        for i in range(chunk_size):
            circular_buffer[buffer_head] = chunk[i]
            buffer_head = (buffer_head + 1) % config.CIRCULAR_BUFFER_SIZE
    else:
        # Trường hợp không rõ ràng - vẫn tăng silence counter nhẹ
        consecutive_silence_count += 1
        # Thêm chunk vào circular buffer
        chunk_size = len(chunk)
        for i in range(chunk_size):
            circular_buffer[buffer_head] = chunk[i]
            buffer_head = (buffer_head + 1) % config.CIRCULAR_BUFFER_SIZE
    
    return buffer_head, buffer_tail, is_recording, consecutive_silence_count

def _should_process_audio(is_recording, consecutive_silence_count, buffer_head, buffer_tail, last_api_call_time):
    """Kiểm tra có nên xử lý audio không"""
    silence_duration = consecutive_silence_count * 0.02  # 20ms per chunk
    
    # Tính thời gian recording hiện tại
    if is_recording:
        if buffer_head >= buffer_tail:
            buffer_size = buffer_head - buffer_tail
        else:
            buffer_size = (config.CIRCULAR_BUFFER_SIZE - buffer_tail) + buffer_head
        current_recording_duration = buffer_size / 32000.0  # 32000 bytes = 1 giây
    else:
        current_recording_duration = 0.0
    
    # Điều kiện xử lý: silence đủ lâu HOẶC đạt max duration
    should_process = (
        is_recording and (
            silence_duration >= config.MIN_SILENCE_DURATION or  # Silence đủ lâu (1.0s)
            current_recording_duration >= config.MAX_RECORDING_DURATION  # Đạt max duration
        )
    )
    
    # Thêm kiểm tra delay để tránh spam API calls
    current_time = time.time()
    time_since_last_api = current_time - last_api_call_time
    if time_since_last_api < config.MIN_API_CALL_DELAY:
        should_process = False
    
    return should_process, current_time

def _process_audio_recognition(circular_buffer, buffer_head, buffer_tail, timestamp, seq, socketio, current_time):
    """Xử lý nhận dạng giọng nói"""
    
    print(f"🎯 BẮT ĐẦU XỬ LÝ AUDIO")
    
    # Trích xuất audio từ circular buffer (từ tail đến head)
    if buffer_head >= buffer_tail:
        # Buffer không bị wrap
        audio_data = bytes(circular_buffer[buffer_tail:buffer_head])
    else:
        # Buffer bị wrap, cần nối 2 phần
        audio_data = bytes(circular_buffer[buffer_tail:]) + bytes(circular_buffer[:buffer_head])
    
    print(f"🎵 Audio: {len(audio_data)} bytes, duration: {len(audio_data)//32000:.1f}s")
    
    # Kiểm tra audio quality
    if len(audio_data) >= 2:
        samples = struct.unpack(f"<{len(audio_data)//2}h", audio_data)
        rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
        max_amplitude = max(abs(s) for s in samples)
        duration_seconds = len(samples) / 16000.0
        
        # Kiểm tra điều kiện xử lý audio
        should_process_audio = (
            rms > (config.MIN_SPEECH_RMS * 0.5) or  # Giảm ngưỡng RMS
            max_amplitude > (config.MIN_AMPLITUDE_THRESHOLD * 0.5) or  # Giảm ngưỡng amplitude
            any(abs(s) > 600 for s in samples) or  # Có ít nhất 1 sample mạnh
            duration_seconds > 0.5  # Audio đủ dài (ít nhất 0.5s)
        )
        
        if should_process_audio:
            print(f"✅ Audio đủ chất lượng để xử lý")
            
            # Áp dụng audio preprocessing
            if config.ENABLE_PREPROCESSING:
                processed_buffer = audio_preprocessing_improved(audio_data)
            else:
                processed_buffer = audio_data
            
            # Lưu audio thành WAV file
            wav_file = save_audio_to_wav(processed_buffer)
            if wav_file:
                try:
                    # Sử dụng Google Speech Recognition để nhận dạng
                    print(f"🔄 Đang gửi lên Google Speech API...")
                    transcription = transcribe_audio_with_google(wav_file, config.GOOGLE_SPEECH_LANGUAGE)
                    
                    if transcription:
                        # Xử lý transcription dựa trên trạng thái
                        if config.is_listening_for_question:
                            # CHẾ ĐỘ NGHE CÂU HỎI
                            process_question_capture(transcription, timestamp, socketio)
                        else:
                            # CHẾ ĐỘ MẶC ĐỊNH
                            # Ghi transcript như bình thường
                            if config.transcript_logger:
                                config.transcript_logger.log_transcript_simple(transcription)
                            
                            # Kiểm tra wake word
                            if check_wake_word(transcription):
                                process_wake_word_detection(transcription, timestamp, seq, socketio)
                            
                            # Gửi kết quả final như bình thường
                            socketio.emit("final", {
                                "text": transcription,
                                "timestamp": timestamp,
                                "seq": seq
                            })
                            print(f"🎯 Final (Google Speech): {transcription}")
                        
                        return True
                    else:
                        print(f"🔇 Google Speech không nhận dạng được text")
                        # Nếu đang nghe câu hỏi mà không nhận dạng được
                        if config.is_listening_for_question:
                            reset_question_mode()
                        return False
                        
                finally:
                    # Xóa file WAV tạm thời
                    try:
                        os.unlink(wav_file)
                    except:
                        pass
            else:
                print(f"❌ Không thể tạo WAV file")
                return False
        else:
            print(f"🔇 Audio không đủ chất lượng")
            return False
    else:
        print(f"🔇 Audio data quá ngắn: {len(audio_data)} bytes")
        return False