#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wake Word Handler - Xử lý wake word detection và state management
"""

import audio_utils.server_config as config
from .udp_handler import send_led_command

def check_wake_word(text):
    """Kiểm tra text có chứa wake word không"""
    if not text:
        return False
    
    # Chuyển về lowercase để so sánh không phân biệt hoa thường
    text_lower = text.lower().strip()
    wake_word_lower = config.WAKE_WORD.lower()
    
    # Kiểm tra wake word có trong text không
    if wake_word_lower in text_lower:
        print(f"🎯 WAKE WORD DETECTED: '{text}' chứa '{config.WAKE_WORD}'")
        return True
    
    return False

def process_wake_word_detection(transcription, timestamp, seq, socketio):
    """Xử lý khi phát hiện wake word"""
    # Kích hoạt chế độ nghe câu hỏi
    config.is_listening_for_question = True
    print("🎯 Wake word detected! Chuyển sang chế độ nghe câu hỏi...")
    
    # Gửi lệnh BẬT đèn xanh liên tục
    send_led_command("LED_GREEN_ON")
    
    # Gửi thông báo wake word đến web interface
    socketio.emit("wake_word", {
        "text": transcription,
        "wake_word": config.WAKE_WORD,
        "timestamp": timestamp,
        "seq": seq
    })

def process_question_capture(transcription, timestamp, socketio):
    """Xử lý khi capture được câu hỏi"""
    print(f"❓ Câu hỏi đã nhận dạng: {transcription}")
    
    # Ghi câu hỏi vào file log riêng
    if config.question_logger:
        config.question_logger.log_transcript_simple(transcription)
    
    # Gửi lệnh tắt đèn xanh
    send_led_command("LED_GREEN_OFF")
    
    # Gửi lên web UI
    socketio.emit("question_captured", {
        "text": transcription,
        "timestamp": timestamp
    })
    
    # Quay lại trạng thái mặc định
    config.is_listening_for_question = False
    print("✅ Đã ghi nhận câu hỏi, quay lại chế độ chờ wake word.")

def reset_question_mode():
    """Reset về chế độ mặc định nếu có lỗi"""
    if config.is_listening_for_question:
        print("🔇 Reset về chế độ mặc định do lỗi")
        send_led_command("LED_GREEN_OFF")
        config.is_listening_for_question = False