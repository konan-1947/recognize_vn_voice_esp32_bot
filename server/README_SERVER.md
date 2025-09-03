# 📘 Server Docs (Tối giản theo 2 mục yêu cầu)

## 1) Luồng hoạt động của chương trình (3 thành phần)

### A. ESP32 (INMP441 + WiFi)
- Thu âm bằng I2S (INMP441) ở 16 kHz, 16-bit, mono.
- Đóng gói từng frame audio (kèm header: seq, time_ms, codec, length) rồi gửi qua UDP tới server `UDP_PORT=5005`.
- Nhận lệnh điều khiển qua UDP `COMMAND_PORT=5006` (ví dụ: `BLINK3`, `LED_GREEN_ON`, `LED_GREEN_OFF`).
- Nhận file WAV qua TCP (mặc định `:8080`) để phát âm thanh từ ESP32 (TTS/AI trả lời).

Dòng dữ liệu: Micro → I2S → (ESP32) UDP → Server.
Dòng điều khiển: Server → UDP command → ESP32 (điều khiển LED, v.v.).
Dòng phát lại: Server → TCP WAV → ESP32 → I2S Out.

### B. Server (Python, modular)
- Thành phần nhận UDP: lắng nghe audio từ ESP32, parse header, đẩy payload PCM vào hàng đợi `q_audio`.
- Thành phần ASR (asr_worker):
  - Dùng circular buffer + lookback để gom câu nói, tránh cụt câu.
  - Tiền xử lý audio (lọc band‑pass, giảm nhiễu, chuẩn hóa) nếu bật.
  - Lưu tạm WAV và gửi lên Google Speech API để nhận dạng (vi‑VN).
  - Phát hiện wake word. Nếu có, chuyển sang chế độ ghi nhận câu hỏi; khi đã có câu hỏi, gọi AI để trả lời và có thể TTS gửi về ESP32 để phát.
  - Ghi transcript ra `transcripts/live_transcript.txt` và đẩy kết quả lên web UI qua Socket.IO.
- Web UI (Flask + Socket.IO): hiển thị transcript theo thời gian thực, endpoint `/status`, `/transcript-stats`.

Dòng xử lý: UDP in → queue → circular buffer → (preprocess) → Google Speech → transcript → (wake word/Q&A) → Socket.IO + TTS/ESP32.

### C. Các dịch vụ khác (tích hợp)
- Google Speech Recognition: chuyển WAV thành text.
- Google Gemini: tạo câu trả lời cho câu hỏi (sau wake word), dùng `GEMINI_API_KEY` trong `.env`.
- gTTS + chuyển đổi MP3→WAV + gửi WAV sang ESP32 để phát (TTS cho câu trả lời AI).

---

## 2) Cách sử dụng + mục đích của từng folder/file

### Cách sử dụng nhanh
1) Cài đặt
```bash
cd server
pip install -r requirements.txt
python -c "from audio_utils import check_audio_dependencies; check_audio_dependencies()"
```
2) Cấu hình (tùy chọn AI)
- Tạo file `.env` trong `server/`:
```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_SYSTEM_PROMPT=Trả lời ngắn gọn, chính xác bằng tiếng Việt.
```
3) Chạy server real‑time
```bash
python google_speech_circular_server.py
# Web: http://localhost:5000, UDP: 5005, Socket.IO: mặc định theo Flask
```
4) Ghi âm kiểm thử (không cần web/UI)
```bash
python audio_test_recorder.py
# Lưu raw + processed WAV và kết quả nhận dạng để so sánh
```

Lưu ý mạng: ESP32 và server phải cùng LAN; chỉnh `SERVER_IP` trong `test_voice3/config.h` (phía firmware ESP32).

---

### Mục đích của từng folder/file (phần server)

- `server/` (gốc)
  - `google_speech_circular_server.py`: Ứng dụng server chính (UDP listener + ASR + Flask/Socket.IO + UI).
  - `audio_test_recorder.py`: Công cụ ghi âm kiểm thử 10s từ UDP để đánh giá chất lượng audio và độ chính xác nhận dạng.
  - `requirements.txt`: Danh sách thư viện Python.
  - `templates/index.html`: Giao diện web hiển thị transcript theo thời gian thực.
  - `transcripts/`:
    - `live_transcript.txt`: File log transcript chạy thật.
  - `README_SERVER.md`: Tài liệu bạn đang đọc.

- `server/audio_utils/` (package chính)
  - `__init__.py`: Xuất các hàm/lớp tiện dụng cho import gọn.
  - `server_config.py`: Hằng số cấu hình server (cổng, ngưỡng RMS, lookback, v.v.), biến trạng thái toàn cục (hàng đợi audio, cờ shutdown, logger,…).
  - `udp_handler.py`: Lắng nghe/gửi UDP (nhận audio từ ESP32, gửi lệnh LED về ESP32 qua `COMMAND_PORT`).
  - `asr_processor.py`: Luồng xử lý ASR:
    - Circular buffer + lookback để gộp câu.
    - Phát hiện speech/silence, giới hạn thời lượng, delay chống spam API.
    - Tiền xử lý audio (lọc band‑pass, giảm nhiễu, normalize) → Google Speech → xuất transcript.
    - Tích hợp wake word/Q&A + phát kết quả lên Socket.IO.
  - `audio_processing.py`: Hàm `audio_preprocessing_improved` (band‑pass 80–7500 Hz, noisereduce, normalize).
  - `speech_recognition.py`: Gọi Google Speech API từ file WAV, trả về text.
  - `flask_server.py`: Tạo Flask app + Socket.IO, routes cơ bản (`/`, `/status`, `/transcript-stats`).
  - `transcript_logger.py`: Ghi transcript ra file, thống kê/backup/clear.
  - `file_utils.py`: Lưu WAV, lưu kết quả nhận dạng ra TXT (phục vụ test recorder).
  - `gemini_api.py`: Gọi Google Gemini tạo câu trả lời (đọc `.env`).
  - `tts_utils.py`: TTS bằng gTTS → MP3 → (chuyển WAV) → phát local hoặc gửi WAV tới ESP32.
  - `esp32_audio_sender.py`: Gửi file WAV sang ESP32 qua TCP (đồng bộ/bất đồng bộ, callback tiến trình).
  - `dependencies.py`: Kiểm tra/cung cấp lệnh cài thư viện cần thiết.

---

### Tham chiếu nhanh cổng/kết nối
- UDP audio in (ESP32 → Server): `5005`.
- UDP command (Server → ESP32): `5006`.
- Flask/Socket.IO (Web UI): `5000`.
- TCP nhận WAV trên ESP32 (phát lại): `8080` (phía ESP32).

### Tham chiếu nhanh pipeline
- Thu âm → UDP → Queue → Circular buffer → Preprocess → Google Speech → Transcript → (Wake word → Hỏi Gemini → TTS) → Gửi WAV → ESP32 phát.
