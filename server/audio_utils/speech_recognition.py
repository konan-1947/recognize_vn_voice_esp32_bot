#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Speech Recognition Module
Chứa các hàm nhận dạng giọng nói chung cho server
"""

import time
import speech_recognition as sr

def transcribe_audio_with_google(wav_file_path, language="vi-VN"):
    """
    Sử dụng Google Speech Recognition để nhận dạng giọng nói
    
    Args:
        wav_file_path (str): Đường dẫn đến file WAV
        language (str): Ngôn ngữ nhận dạng (mặc định: vi-VN)
    
    Returns:
        str: Text đã được nhận dạng, hoặc "" nếu không nhận dạng được
    """
    try:
        # Khởi tạo recognizer
        recognizer = sr.Recognizer()
        
        # Cấu hình parameters tối ưu
        recognizer.energy_threshold = 100
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8
        recognizer.non_speaking_duration = 0.3
        recognizer.phrase_threshold = 0.3
        recognizer.operation_timeout = 15
        
        # Đọc audio file
        with sr.AudioFile(wav_file_path) as source:
            print(f"🎤 Đang đọc audio file: {wav_file_path}")
            # Điều chỉnh cho ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.1)
            audio = recognizer.record(source)
        
        # Nhận dạng với Google Speech
        print(f"🔄 Đang gửi đến Google Speech API...")
        start_time = time.time()
        
        text = recognizer.recognize_google(
            audio,
            language=language,
            show_all=False
        )
        
        processing_time = time.time() - start_time
        print(f"✅ Google Speech xử lý xong trong {processing_time:.2f}s")
        
        return text.strip()
        
    except sr.UnknownValueError:
        print("🔇 Google Speech không thể nhận dạng được giọng nói")
        return ""
    except sr.RequestError as e:
        print(f"❌ Lỗi Google Speech API: {e}")
        return ""
    except Exception as e:
        print(f"❌ Lỗi xử lý Google Speech: {e}")
        return "" 