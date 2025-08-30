#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio Processing Module
Chứa các hàm xử lý audio chung cho server
"""

import numpy as np
import noisereduce as nr
from scipy.signal import butter, lfilter

def butter_bandpass(lowcut, highcut, fs, order=5):
    """Thiết kế một bộ lọc band-pass Butterworth."""
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    """Áp dụng bộ lọc band-pass Butterworth."""
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y

def audio_preprocessing_improved(audio_data, sample_rate=16000):
    """
    Chuỗi xử lý âm thanh được cải thiện:
    1. Band-pass filter để tập trung vào tần số giọng nói.
    2. Noise reduction chuyên dụng để loại bỏ tạp âm nền (tiếng mưa, gió).
    3. Normalize âm lượng.
    
    Args:
        audio_data (bytes): Audio data dạng bytes
        sample_rate (int): Sample rate của audio (mặc định: 16000)
    
    Returns:
        bytes: Audio đã được xử lý
    """
    try:
        # Chuyển bytes thành numpy array float32 để xử lý
        samples_int16 = np.frombuffer(audio_data, dtype=np.int16)
        samples_float32 = samples_int16.astype(np.float32) / 32768.0

        # ===== BƯỚC 1: Lọc Band-pass (80Hz - 7500Hz) =====
        # Giữ lại dải tần cốt lõi của giọng nói và loại bỏ tiếng ù tần số thấp,
        # và tiếng rít tần số quá cao.
        # Sử dụng scipy để có bộ lọc chất lượng cao.
        filtered_samples = butter_bandpass_filter(samples_float32, 80, 7500, sample_rate, order=4)
        print("🔧 Step 1: Applied Band-pass filter (80Hz - 7.5kHz)")

        # ===== BƯỚC 2: Giảm tạp âm (Noise Reduction) =====
        # Sử dụng thư viện noisereduce, rất hiệu quả với tiếng ồn nền.
        # Thư viện sẽ tự động xác định đâu là noise và đâu là giọng nói.
        reduced_noise_samples = nr.reduce_noise(y=filtered_samples, sr=sample_rate)
        print("🔧 Step 2: Applied professional noise reduction")

        # ===== BƯỚC 3: Normalize và chuyển về int16 =====
        # Đưa âm lượng lớn nhất về gần mức tối đa để âm thanh to và rõ hơn.
        max_val = np.max(np.abs(reduced_noise_samples))
        if max_val > 0:
            normalized_samples = reduced_noise_samples / max_val * 0.95  # Normalize to 95%
        else:
            normalized_samples = reduced_noise_samples
        print("🔧 Step 3: Normalized audio volume")

        # Chuyển đổi lại sang định dạng int16 để lưu file WAV
        processed_samples_int16 = (normalized_samples * 32767).astype(np.int16)
        
        print("✅ Audio preprocessing finished successfully!")
        
        return processed_samples_int16.tobytes()

    except Exception as e:
        print(f"❌ Lỗi audio preprocessing: {e}")
        return audio_data 