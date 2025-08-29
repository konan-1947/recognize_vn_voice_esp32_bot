# 🎤 ESP32 + INMP441 Real-time Voice Recognition Server

Hệ thống nhận dạng giọng nói thời gian thực sử dụng ESP32 với microphone INMP441, kết hợp Google Speech Recognition API và Circular Buffer để xử lý audio liên tục.

## ✨ Tính năng chính

- **Real-time Audio Streaming**: Nhận audio từ ESP32 qua UDP
- **Circular Buffer**: Xử lý audio liên tục với lookback để không bị cụt câu
- **Google Speech Recognition**: Sử dụng Google Speech API với hỗ trợ tiếng Việt
- **Web Interface**: Giao diện web real-time với Socket.IO
- **Audio Preprocessing**: Lọc nhiễu, nén động, high-pass filter
- **Multi-threading**: UDP listener và ASR worker chạy song song

## 🏗️ Kiến trúc hệ thống

```
ESP32 + INMP441 → UDP → Python Server → Google Speech API → Web Interface
     ↓              ↓         ↓              ↓              ↓
  Microphone   Audio Packets  Circular    Recognition   Real-time
  Streaming                   Buffer      Results       Display
```

## 📋 Yêu cầu hệ thống

### Hardware
- **ESP32**: ESP32-WROOM-32 hoặc tương tự
- **INMP441**: I2S MEMS Microphone
- **Kết nối**: WiFi để giao tiếp với server

### Software
- **Python**: 3.7+
- **OS**: Windows, Linux, macOS
- **Internet**: Kết nối ổn định cho Google Speech API

## 🚀 Cài đặt

### 1. Clone repository
```bash
git clone <repository-url>
cd test_voice2
```

### 2. Cài đặt Python dependencies
```bash
cd server
pip install -r requirements.txt
```

### 3. Kết nối phần cứng
- Xem `PIN_CONFIGURATION.md` để biết cấu hình chân chi tiết
- Xem `WIRING_DIAGRAM.md` để biết sơ đồ kết nối trực quan
- Kết nối ESP32 với INMP441 theo hướng dẫn

### 4. Upload code Arduino
- Mở `test_voice2.ino` trong Arduino IDE
- Cài đặt ESP32 board support
- Cập nhật WiFi credentials trong `config.h`
- Upload code lên ESP32

### 5. Cấu hình server
- Kiểm tra IP của ESP32 trong Serial Monitor
- Cập nhật `SERVER_IP` trong `config.h` nếu cần
- Đảm bảo port 5005 (UDP) và 5000 (HTTP) không bị block

## 🔧 Sử dụng

### Khởi động server
```bash
cd server
python google_speech_circular_server.py
```

### Truy cập web interface
- Mở browser: `http://localhost:5000`
- Giao diện sẽ hiển thị transcript real-time

### Kết nối ESP32
- Đảm bảo ESP32 đã kết nối WiFi
- Kiểm tra Serial Monitor: "Hệ thống đã sẵn sàng streaming âm thanh!"
- Server sẽ tự động nhận audio packets

## ⚙️ Cấu hình

### Audio Processing
```python
ENABLE_PREPROCESSING = True      # Bật preprocessing
SILENCE_THRESHOLD = 0.01         # Ngưỡng tiếng ồn
CIRCULAR_BUFFER_SIZE = 512000    # Buffer size (16s)
LOOKBACK_SIZE = 128000           # Lookback (4s)
```

### Google Speech
```python
GOOGLE_SPEECH_LANGUAGE = "vi-VN"  # Tiếng Việt
GOOGLE_SPEECH_TIMEOUT = 5         # Timeout 5s
```

### Network
```python
HOST = "0.0.0.0"                 # Bind tất cả interfaces
UDP_PORT = 5005                   # Port UDP
FLASK_PORT = 5000                 # Port HTTP
```

## 📁 Cấu trúc dự án

```
test_voice2/
├── config.h                          # Cấu hình Arduino
├── test_voice2.ino                  # Code Arduino chính
├── .gitignore                       # Git ignore rules
├── README.md                        # Tài liệu này
├── PIN_CONFIGURATION.md             # Cấu hình chân chi tiết
├── WIRING_DIAGRAM.md                # Sơ đồ kết nối trực quan
└── server/
    ├── google_speech_circular_server.py  # Server chính
    ├── requirements.txt             # Python dependencies
    ├── INSTALL_LINUX.md            # Hướng dẫn cài đặt Linux
    ├── INSTALL_WINDOWS.md          # Hướng dẫn cài đặt Windows
    ├── templates/
    │   └── index.html              # Web interface
    └── vosk-model-*/               # Speech models (optional)
```

## 🌐 API Endpoints

- **`/`**: Web interface chính
- **`/status`**: Trạng thái server
- **`/test`**: Test kết nối

## 🔍 Troubleshooting

### ESP32 không kết nối
- Kiểm tra WiFi credentials
- Đảm bảo ESP32 và server cùng mạng
- Kiểm tra firewall settings

### Audio không được nhận dạng
- Kiểm tra kết nối internet
- Đảm bảo microphone hoạt động
- Điều chỉnh `SILENCE_THRESHOLD` và `MIN_SPEECH_RMS`

### Server không khởi động
- Kiểm tra Python version (3.7+)
- Cài đặt đầy đủ dependencies
- Kiểm tra port availability

## 📊 Performance

- **Latency**: ~2-5 giây (tùy thuộc internet)
- **Buffer Size**: 16 giây audio
- **Lookback**: 4 giây để tránh cụt câu
- **Sample Rate**: 16kHz, 16-bit mono

## 🤝 Đóng góp

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## 📄 License

Dự án này được phát hành dưới MIT License.

## 📞 Hỗ trợ

Nếu gặp vấn đề, vui lòng:
- Kiểm tra troubleshooting section
- Tạo issue trên GitHub
- Liên hệ maintainer

---

**Made with ❤️ for Vietnamese speech recognition** 