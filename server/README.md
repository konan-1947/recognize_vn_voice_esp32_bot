# Audio Server - Modular Architecture

## 📁 Cấu trúc thư mục

```
server/
├── audio_utils/                    # Audio utilities package
│   ├── __init__.py                # Package initialization
│   ├── audio_processing.py        # Audio preprocessing functions
│   ├── speech_recognition.py      # Google Speech API integration
│   ├── file_utils.py              # WAV and TXT file handling
│   ├── dependencies.py            # Library dependency checker
│   └── transcript_logger.py       # Transcript logging utility
├── google_speech_circular_server.py # Main server (real-time speech recognition)
├── audio_test_recorder.py         # Test recorder for audio quality
├── requirements.txt               # Python dependencies
├── templates/                     # Web interface templates
│   └── index.html
├── transcripts/                   # Transcript log files
│   └── live_transcript.txt       # Live transcript log
└── README.md                      # This file
```

## 🚀 Cài đặt

### 1. Cài đặt dependencies
```bash
cd server
pip install -r requirements.txt
```

### 2. Kiểm tra dependencies
```bash
python -c "from audio_utils import check_audio_dependencies; check_audio_dependencies()"
```

## 📚 Modules

### `audio_utils.audio_processing`
- **`audio_preprocessing_improved()`**: Chuỗi xử lý âm thanh chuyên nghiệp
  - Band-pass filter (80Hz - 7.5kHz)
  - Professional noise reduction
  - Audio normalization

### `audio_utils.speech_recognition`
- **`transcribe_audio_with_google()`**: Nhận dạng giọng nói với Google Speech API
  - Hỗ trợ tiếng Việt (vi-VN)
  - Cấu hình tối ưu cho real-time

### `audio_utils.file_utils`
- **`save_audio_to_wav()`**: Lưu audio thành WAV với thống kê chi tiết
- **`save_transcription_to_txt()`**: Lưu kết quả nhận dạng vào TXT

### `audio_utils.dependencies`
- **`check_audio_dependencies()`**: Kiểm tra thư viện cần thiết
- **`get_installation_commands()`**: Lệnh cài đặt dependencies

### `audio_utils.transcript_logger`
- **`TranscriptLogger`**: Class để ghi transcriptions ra file txt
  - **`log_transcript_simple()`**: Ghi text đơn giản (chỉ text, không timestamp)
  - **`log_transcript()`**: Ghi text với timestamp
  - **`get_stats()`**: Xem thống kê file log
  - **`backup_log()`**: Backup file log
  - **`clear_log()`**: Xóa và tạo log mới

## 🎯 Sử dụng

### 1. Real-time Speech Recognition Server
```bash
python google_speech_circular_server.py
```
- UDP port: 5005
- Web interface: http://localhost:5000
- Circular buffer với lookback
- Auto-send sau 10s hoặc khi im lặng

### 2. Audio Test Recorder
```bash
python audio_test_recorder.py
```
- Ghi âm test 10 giây
- Lưu raw + processed WAV
- Test Google Speech với cả hai
- So sánh độ chính xác

## 🔧 Tính năng

### Audio Processing
- **Band-pass filtering**: Tập trung vào tần số giọng nói
- **Noise reduction**: Loại bỏ tiếng ồn nền chuyên nghiệp
- **Normalization**: Chuẩn hóa âm lượng

### Speech Recognition
- **Google Speech API**: Độ chính xác cao
- **Vietnamese support**: Hỗ trợ tiếng Việt
- **Real-time**: Xử lý liên tục

### File Management
- **WAV format**: Chất lượng cao, 16-bit
- **TXT output**: Kết quả nhận dạng có cấu trúc
- **Statistics**: RMS, amplitude, dynamic range

## 📊 Output Files

### WAV Files
```
raw_test_recording_20241201_143022_rms1200_max28000.wav
processed_test_recording_20241201_143022_rms1200_max28000.wav
```

### TXT Files
```
raw_test_recording_20241201_143022_rms1200_max28000.txt
processed_test_recording_20241201_143022_rms1200_max28000.txt
```

### Transcript Log Files
```
transcripts/
├── live_transcript.txt           # Live transcript log (main server)
└── transcript_log_backup_*.txt   # Backup files
```

## 🎤 ESP32 + INMP441 Setup

### Arduino Code
```cpp
// test_voice3.ino
#include "config.h"

// UDP streaming to server:5005
// Sample rate: 16kHz
// Format: 16-bit mono
```

### Hardware
- **ESP32**: WiFi + UDP streaming
- **INMP441**: I2S microphone
- **Connection**: WiFi network

## 🔍 Troubleshooting

### Dependencies Issues
```bash
# Kiểm tra
python -c "from audio_utils import check_audio_dependencies; check_audio_dependencies()"

# Cài đặt lại
pip install -r requirements.txt
```

### Audio Quality Issues
1. Chạy `audio_test_recorder.py` để test
2. So sánh raw vs processed audio
3. Kiểm tra WAV files và TXT results
4. Điều chỉnh parameters trong `audio_processing.py`

### Speech Recognition Issues
1. Kiểm tra internet connection
2. Test với `audio_test_recorder.py`
3. So sánh raw vs processed recognition
4. Điều chỉnh language code (vi-VN)

## 🚀 Development

### Thêm module mới
1. Tạo file trong `audio_utils/`
2. Thêm import vào `__init__.py`
3. Cập nhật `__all__` list
4. Test với main applications

### Cập nhật dependencies
1. Cập nhật `requirements.txt`
2. Test với `check_audio_dependencies()`
3. Cập nhật documentation

## 📝 License

MIT License - Sử dụng tự do cho mục đích giáo dục và thương mại. 