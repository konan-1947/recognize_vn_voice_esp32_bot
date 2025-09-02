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

def convert_mp3_to_wav(mp3_file, wav_file=None):
    """
    Chuyển đổi file MP3 sang WAV để ESP32 có thể phát
    Sử dụng miniaudio để decode MP3 và wave để ghi WAV
    
    Args:
        mp3_file (str): Đường dẫn file MP3
        wav_file (str): Đường dẫn file WAV output (tùy chọn)
        
    Returns:
        str: Đường dẫn file WAV hoặc None nếu lỗi
    """
    try:
        import miniaudio
        import wave
        import numpy as np
        
        if not os.path.exists(mp3_file):
            print(f"❌ File MP3 không tồn tại: {mp3_file}")
            return None
        
        # Tạo tên file WAV nếu không được cung cấp
        if not wav_file:
            base_name = os.path.splitext(mp3_file)[0]
            wav_file = f"{base_name}.wav"
        
        # Decode MP3 thành PCM
        decoded = miniaudio.decode_file(mp3_file)
        print(f"📊 MP3 Info - Sample rate: {decoded.sample_rate}, Channels: {decoded.nchannels}, Sample width: {decoded.sample_width} bytes")
        
        # Convert sang format tương thích với ESP32 nếu cần
        samples = decoded.samples
        sample_rate = decoded.sample_rate
        nchannels = decoded.nchannels
        sample_width = decoded.sample_width
        
        # Chuyển sang 16kHz mono 16-bit nếu cần thiết
        if decoded.nchannels > 1 or decoded.sample_rate != 16000:
            # Convert numpy array để xử lý
            if decoded.sample_width == 2:  # 16-bit
                audio_array = np.frombuffer(samples, dtype=np.int16)
            elif decoded.sample_width == 4:  # 32-bit
                audio_array = np.frombuffer(samples, dtype=np.int32)
                # Convert về 16-bit
                audio_array = (audio_array / 65536).astype(np.int16)
            else:
                audio_array = np.frombuffer(samples, dtype=np.int16)
            
            # Chuyển sang mono nếu stereo
            if decoded.nchannels == 2:
                audio_array = audio_array.reshape(-1, 2)
                audio_array = np.mean(audio_array, axis=1).astype(np.int16)
                nchannels = 1
            
            # Resample về 16kHz nếu cần (đơn giản bằng cách skip samples)
            if decoded.sample_rate != 16000:
                ratio = decoded.sample_rate / 16000
                new_length = int(len(audio_array) / ratio)
                indices = np.linspace(0, len(audio_array) - 1, new_length).astype(int)
                audio_array = audio_array[indices]
                sample_rate = 16000
            
            samples = audio_array.tobytes()
            sample_width = 2  # 16-bit
        
        # Ghi ra file WAV
        with wave.open(wav_file, "wb") as wf:
            wf.setnchannels(nchannels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(samples)
        
        print(f"✅ Đã chuyển đổi MP3 -> WAV: {wav_file} (Rate: {sample_rate}Hz, Channels: {nchannels}, Width: {sample_width} bytes)")
        return wav_file
        
    except ImportError:
        print("❌ Cần cài đặt miniaudio: pip install miniaudio")
        return None
    except Exception as e:
        print(f"❌ Lỗi chuyển đổi MP3 -> WAV: {e}")
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

def text_to_speech_esp32(text, esp32_ip="192.168.1.18", esp32_port=8080, language='vi', slow=False):
    """
    Chuyển text thành âm thanh và gửi tới ESP32 thay vì phát từ loa máy tính
    
    Args:
        text (str): Văn bản cần đọc
        esp32_ip (str): IP của ESP32
        esp32_port (int): Port TCP của ESP32
        language (str): Ngôn ngữ
        slow (bool): Tốc độ đọc
        
    Returns:
        bool: True nếu gửi thành công
    """
    try:
        # Import ESP32AudioSender từ cùng package
        from .esp32_audio_sender import send_audio_to_esp32_async
        
        # Tạo file MP3
        mp3_file = text_to_audio_file(text, language, slow)
        if not mp3_file:
            return False
        
        # Chuyển đổi MP3 -> WAV
        wav_file = convert_mp3_to_wav(mp3_file)
        if not wav_file:
            return False
        
        # Gửi WAV tới ESP32 bất đồng bộ
        def on_success(file_path):
            print(f"✅ Đã gửi TTS tới ESP32: {os.path.basename(file_path)}")
            # Dọn dẹp file tạm
            try:
                os.remove(mp3_file)
                os.remove(wav_file)
            except:
                pass
        
        def on_error(error_msg):
            print(f"❌ Lỗi gửi TTS tới ESP32: {error_msg}")
            # Dọn dẹp file tạm
            try:
                os.remove(mp3_file)
                os.remove(wav_file)
            except:
                pass
        
        # Gửi bất đồng bộ
        thread = send_audio_to_esp32_async(wav_file, esp32_ip, esp32_port, on_success, on_error)
        print(f"🔊 Đã gửi TTS '{text[:50]}...' tới ESP32")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi TTS -> ESP32: {e}")
        return False

def text_to_speech(text, language='vi', slow=False, auto_play=True, esp32_mode=False, esp32_ip="192.168.1.18", esp32_port=8080):
    """
    Chuyển text thành âm thanh và tự động phát HOẶC gửi tới ESP32
    
    Args:
        text (str): Văn bản cần đọc
        language (str): Ngôn ngữ
        slow (bool): Tốc độ đọc
        auto_play (bool): Tự động phát sau khi tạo (chỉ khi esp32_mode=False)
        esp32_mode (bool): Nếu True, gửi tới ESP32 thay vì phát từ loa máy tính
        esp32_ip (str): IP của ESP32 (khi esp32_mode=True)
        esp32_port (int): Port TCP của ESP32 (khi esp32_mode=True)
        
    Returns:
        str|bool: Đường dẫn file âm thanh (local mode) hoặc True/False (ESP32 mode)
    """
    if esp32_mode:
        # Gửi tới ESP32
        return text_to_speech_esp32(text, esp32_ip, esp32_port, language, slow)
    else:
        # Chế độ cũ: phát từ loa máy tính
        audio_file = text_to_audio_file(text, language, slow)
        
        if audio_file and auto_play:
            play_audio_file(audio_file)
        
        return audio_file