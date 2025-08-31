#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS Utils - Simple Text-to-Speech utility
Chỉ nhận chuỗi vào và trả về file âm thanh
"""

import os
import tempfile
import time
from gtts import gTTS
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("⚠️ pygame không có, sẽ sử dụng phương pháp fallback")

def text_to_audio_file(text, language='vi', slow=False, output_dir=None):
    """
    Chuyển đổi text thành file âm thanh MP3
    
    Args:
        text (str): Văn bản cần chuyển đổi
        language (str): Ngôn ngữ (vi: tiếng Việt, en: tiếng Anh)
        slow (bool): Tốc độ đọc (False: bình thường, True: chậm)
        output_dir (str): Thư mục lưu file (mặc định: temp)
        
    Returns:
        str: Đường dẫn file âm thanh đã tạo hoặc None nếu lỗi
    """
    try:
        if not text or not text.strip():
            print("⚠️ TTS: Text rỗng, bỏ qua")
            return None
        
        # Tạo đối tượng gTTS
        tts = gTTS(text=text.strip(), lang=language, slow=slow)
        
        # Tạo đường dẫn file output
        if not output_dir:
            output_dir = tempfile.gettempdir()
        
        timestamp = int(time.time() * 1000)
        output_file = os.path.join(output_dir, f"tts_{timestamp}.mp3")
        
        # Lưu file âm thanh
        tts.save(output_file)
        print(f"✅ TTS: Đã tạo file: {output_file}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ TTS: Lỗi tạo file audio: {e}")
        return None

def play_audio_file(audio_file):
    """
    Phát file âm thanh trực tiếp không mở media player
    
    Args:
        audio_file (str): Đường dẫn file âm thanh
        
    Returns:
        bool: True nếu thành công
    """
    try:
        if not os.path.exists(audio_file):
            print(f"❌ File không tồn tại: {audio_file}")
            return False
        
        if PYGAME_AVAILABLE:
            # Sử dụng pygame để phát audio trực tiếp
            try:
                pygame.mixer.init()
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                
                # Đợi phát xong
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)
                
                pygame.mixer.quit()
                print(f"🔊 Đã phát audio: {os.path.basename(audio_file)}")
                return True
                
            except Exception as e:
                print(f"❌ Lỗi pygame: {e}, fallback sang Windows API")
                # Fallback nếu pygame lỗi
        
        # Fallback: Sử dụng Windows API để phát âm thanh im lặng
        import winsound
        winsound.PlaySound(audio_file, winsound.SND_FILENAME)
        print(f"🔊 Đã phát audio (winsound): {os.path.basename(audio_file)}")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi phát audio: {e}")
        return False

def text_to_speech(text, language='vi', slow=False, auto_play=True):
    """
    Chuyển text thành âm thanh và tự động phát
    
    Args:
        text (str): Văn bản cần đọc
        language (str): Ngôn ngữ
        slow (bool): Tốc độ đọc
        auto_play (bool): Tự động phát sau khi tạo
        
    Returns:
        str: Đường dẫn file âm thanh
    """
    audio_file = text_to_audio_file(text, language, slow)
    
    if audio_file and auto_play:
        play_audio_file(audio_file)
    
    return audio_file