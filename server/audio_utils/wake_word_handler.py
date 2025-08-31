#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wake Word Handler - Xử lý wake word detection và state management
Bao gồm tích hợp Gemini AI để trả lời câu hỏi tự động
"""

import audio_utils.server_config as config
from .udp_handler import send_led_command
from .gemini_api import ask_gemini

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
    """Xử lý khi capture được câu hỏi và tạo AI response"""
    print(f"❓ Câu hỏi đã nhận dạng: {transcription}")
    
    # Gửi lệnh tắt đèn xanh
    send_led_command("LED_GREEN_OFF")
    
    # Tạo AI response bằng Gemini
    print("🤖 Đang tạo AI response...")
    ai_response = ask_gemini(transcription)
    
    # Chuẩn bị log entry với cả câu hỏi và câu trả lời
    if ai_response:
        # Tạo log entry bao gồm cả câu hỏi và AI response
        log_entry = f"[{timestamp}]\n❓ Câu hỏi: {transcription}\n🤖 AI trả lời: {ai_response}\n{'-' * 80}"
        print(f"✅ AI response: {ai_response}")
    else:
        # Nếu không có AI response, chỉ log câu hỏi
        log_entry = f"[{timestamp}]\n❓ Câu hỏi: {transcription}\n❌ AI response: Không thể tạo phản hồi\n{'-' * 80}"
        print("❌ Không thể tạo AI response")
    
    # Ghi vào file log câu hỏi (bao gồm AI response)
    if config.question_logger:
        config.question_logger.log_transcript_simple(log_entry)
    
    # Gửi lên web UI bao gồm cả câu hỏi và AI response
    socketio.emit("question_captured", {
        "text": transcription,
        "ai_response": ai_response,
        "timestamp": timestamp,
        "has_ai_response": ai_response is not None
    })
    
    # Quay lại trạng thái mặc định
    config.is_listening_for_question = False
    print("✅ Đã ghi nhận câu hỏi và AI response, quay lại chế độ chờ wake word.")

def reset_question_mode():
    """Reset về chế độ mặc định nếu có lỗi"""
    if config.is_listening_for_question:
        print("🔇 Reset về chế độ mặc định do lỗi")
        send_led_command("LED_GREEN_OFF")
        config.is_listening_for_question = False