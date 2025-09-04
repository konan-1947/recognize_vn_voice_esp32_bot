// ===== CẤU HÌNH KẾT NỐI =====
// Thay đổi thông tin WiFi và server tại đây

// Thông tin WiFi
#define WIFI_SSID "Router1"        // Thay bằng SSID WiFi của bạn
#define WIFI_PASS "dangVuDinh"    // Thay bằng mật khẩu WiFi của bạn

// Thông tin server Python - Moved to secrets.h to avoid conflicts
// #define SERVER_IP "192.168.1.35"          // IP máy chạy Python server
// #define SERVER_PORT 5005                  // Port UDP (có thể giữ nguyên)

// ===== CẤU HÌNH I2S PINS =====
// Điều chỉnh chân kết nối theo board ESP32 của bạn
#define I2S_WS   18   // LRCL (Word Select) - GPIO18
#define I2S_SCK  14   // BCLK (Bit Clock)  - GPIO14
#define I2S_SD   32   // DOUT (Data Out từ INMP441) - GPIO32

// ===== CẤU HÌNH AUDIO =====
#define SAMPLE_RATE     16000             // Sample rate (Hz) - KHÔNG THAY ĐỔI
#define FRAME_MS        20                // Frame length (ms) - KHÔNG THAY ĐỔI
#define AUDIO_GAIN      11                // Bit shift cho gain (11, 12, 13, 14)

// ===== CẤU HÌNH NÂNG CAO =====
#define ENABLE_ULAW     0                 // 0=PCM, 1=μ-law compression
#define ENABLE_VAD      0                 // 0=không VAD, 1=có VAD
#define HEARTBEAT_MS    1000              // Gửi heartbeat mỗi 1 giây 

// ===== CẤU HÌNH AUDIO PLAYBACK =====
// Thông tin để nhận file audio từ server
#define AUDIO_TCP_PORT  8080              // Port TCP để nhận file audio
#define MAX_FILENAME_LENGTH 64            // Độ dài tối đa tên file 

// ===== CẤU HÌNH ANIMATION DIRECTORS =====
// Timing constants cho animation system
#define BLINK_INTERVAL_MIN  2000          // Khoảng cách tối thiểu giữa các lần chớp mắt (ms)
#define BLINK_INTERVAL_MAX  8000          // Khoảng cách tối đa giữa các lần chớp mắt (ms)

#define NEUTRAL_DWELL_MIN   3000          // Thời gian tối thiểu ở trạng thái neutral (ms)
#define NEUTRAL_DWELL_MAX   8000          // Thời gian tối đa ở trạng thái neutral (ms)

#define EMOTION_DWELL_MIN   2000          // Thời gian tối thiểu ở trạng thái cảm xúc (ms)
#define EMOTION_DWELL_MAX   5000          // Thời gian tối đa ở trạng thái cảm xúc (ms)