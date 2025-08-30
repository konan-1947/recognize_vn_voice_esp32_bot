#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dependencies Checker Module
Kiểm tra các thư viện cần thiết cho audio processing
"""

def check_audio_dependencies():
    """
    Kiểm tra các thư viện cần thiết cho audio processing
    
    Returns:
        bool: True nếu tất cả dependencies đã được cài đặt
    """
    dependencies_status = True
    
    try:
        import noisereduce
        print("✅ noisereduce library đã được cài đặt")
    except ImportError:
        print("❌ noisereduce library chưa được cài đặt")
        print("📦 Cài đặt: pip install noisereduce")
        dependencies_status = False
    
    try:
        from scipy.signal import butter, lfilter
        print("✅ scipy library đã được cài đặt")
    except ImportError:
        print("❌ scipy library chưa được cài đặt")
        print("📦 Cài đặt: pip install scipy")
        dependencies_status = False
    
    try:
        import numpy
        print("✅ numpy library đã được cài đặt")
    except ImportError:
        print("❌ numpy library chưa được cài đặt")
        print("📦 Cài đặt: pip install numpy")
        dependencies_status = False
    
    try:
        import speech_recognition
        print("✅ speech_recognition library đã được cài đặt")
    except ImportError:
        print("❌ speech_recognition library chưa được cài đặt")
        print("📦 Cài đặt: pip install SpeechRecognition")
        dependencies_status = False
    
    return dependencies_status

def get_installation_commands():
    """
    Trả về các lệnh cài đặt dependencies
    
    Returns:
        str: Các lệnh cài đặt
    """
    return """
📦 Cài đặt tất cả dependencies:
pip install noisereduce scipy numpy SpeechRecognition

📦 Hoặc cài đặt từng cái:
pip install noisereduce
pip install scipy
pip install numpy
pip install SpeechRecognition
""" 