// ===== ESP32 + INMP441 → UDP PCM16LE 16kHz mono =====
#include <WiFi.h>
#include <WiFiUdp.h>
#include "driver/i2s.h"
#include "config.h"  // File cấu hình WiFi và pins

// Thêm thư viện cho audio playback
#include "SPIFFS.h"
#include "AudioFileSourceSPIFFS.h"
#include "AudioGeneratorWAV.h"
#include "AudioOutputI2S.h"

// ---- Audio params ----
#define SAMPLES_PER_FR  (SAMPLE_RATE * FRAME_MS / 1000)  // 320
#define BYTES_PER_SMP   2   // int16_t
#define FRAME_BYTES     (SAMPLES_PER_FR * BYTES_PER_SMP) // 640

// ---- LED Control ----
#define LED_BUILTIN 2  // Built-in LED trên GPIO 2
#define COMMAND_PORT 5006  // Port để nhận lệnh từ server

// ---- Audio Playback Configuration ----
#define I2S_BCLK_PIN 26  // I2S Bit Clock pin
#define I2S_LRC_PIN 27   // I2S Left/Right Clock pin
#define I2S_DOUT_PIN 25  // I2S Data Out pin
#define TCP_PORT 8080    // Port cho TCP Server nhận file audio
// *** SỬA LỖI: Chỉ định port I2S số 1 cho việc phát nhạc ***
#define I2S_PORT_PLAYER I2S_NUM_1

WiFiUDP udp;
WiFiUDP cmdUdp;  // UDP socket riêng để nhận lệnh
uint32_t seq = 0;
uint32_t t0ms = 0;

// Audio playback objects
AudioGeneratorWAV *wav;
AudioFileSourceSPIFFS *file;
AudioOutputI2S *out;

// TCP server for receiving audio files
WiFiServer server(TCP_PORT);
bool playRequest = false;
String filenameToPlay;  // Chỉ lưu tên file, không có dấu "/"

// *** THÊM MỚI: Biến trạng thái để kiểm soát micro ***
bool isMicStreaming = true;

// Header 12B
struct __attribute__((packed)) PacketHeader {
  uint32_t seq;
  uint32_t t_ms;
  uint8_t  codec; // 0=PCM16LE, 1=μ-law
  uint8_t  len_b2; // len 24-bit (b2:b1:b0)
  uint8_t  len_b1;
  uint8_t  len_b0;
};

static inline void write_len24(PacketHeader& h, uint32_t n) {
  h.len_b2 = (n >> 16) & 0xFF;
  h.len_b1 = (n >> 8)  & 0xFF;
  h.len_b0 = (n)       & 0xFF;
}

void blinkLED(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(200);
    digitalWrite(LED_BUILTIN, LOW);
    delay(200);
  }
}

void handleCommand() {
  int packetSize = cmdUdp.parsePacket();
  if (packetSize > 0) {
    char commandBuffer[32];
    int len = cmdUdp.read(commandBuffer, sizeof(commandBuffer) - 1);
    commandBuffer[len] = '\0';

    String command = String(commandBuffer);
    Serial.println("Nhận lệnh: " + command);

    if (command == "BLINK3") {
      Serial.println("💡 Thực hiện bấm nhấp LED 3 lần!");
      blinkLED(3);
    } else if (command == "LED_GREEN_ON") {
      Serial.println("🟢 Bật đèn xanh liên tục!");
      digitalWrite(LED_BUILTIN, HIGH);
    } else if (command == "LED_GREEN_OFF") {
      Serial.println("⚫ Tắt đèn xanh!");
      digitalWrite(LED_BUILTIN, LOW);
    } else {
      Serial.println("Lệnh không hợp lệ: " + command);
    }
  }
}

// *** CHỈNH SỬA: Hàm này sẽ tắt mic, phát nhạc, xóa file và bật lại mic ***
void handleAudioPlayback() {
  if (playRequest) {
    playRequest = false;

    // --- Tắt micro trước khi phát nhạc ---
    if (isMicStreaming) {
      Serial.println("[MIC] Tạm dừng microphone để phát nhạc...");
      i2s_driver_uninstall(I2S_NUM_0); // Gỡ cài đặt driver I2S port 0
      isMicStreaming = false;
    }
    // ------------------------------------

    String fullPath = "/" + filenameToPlay;
    Serial.printf("[PLAYER] Bắt đầu phát file: %s trên I2S Port %d\n", fullPath.c_str(), I2S_PORT_PLAYER);

    file = new AudioFileSourceSPIFFS(fullPath.c_str());
    wav = new AudioGeneratorWAV();

    if (wav->begin(file, out)) {
      while (wav->isRunning()) {
        if (!wav->loop()) {
          wav->stop();
          Serial.println("[PLAYER] Phát nhạc hoàn tất.");
        }
      }
    } else {
      Serial.println("[ERROR] Không thể bắt đầu phát file WAV. File có thể bị lỗi hoặc không tồn tại.");
    }

    delete wav;
    delete file;

    // *** THÊM MỚI: Xóa file sau khi phát xong ***
    if (SPIFFS.remove(fullPath.c_str())) {
      Serial.printf("[SPIFFS] Đã xóa file: %s\n", fullPath.c_str());
    } else {
      Serial.printf("[ERROR] Không thể xóa file: %s\n", fullPath.c_str());
    }

    // --- Bật lại micro sau khi phát xong ---
    if (!isMicStreaming) {
      Serial.println("[MIC] Khởi động lại microphone...");
      setupI2S_Microphone(); // Gọi lại hàm cài đặt I2S cho micro
      isMicStreaming = true;
    }
    // ------------------------------------

    Serial.println("\n[SERVER] Đang chờ kết nối tiếp theo...");
  }
}

void handleTCPServer() {
  WiFiClient client = server.available();
  if (client) {
    Serial.println("[SERVER] Client đã kết nối!");

    String header = client.readStringUntil('\n');
    header.trim();

    int colonIndex = header.indexOf(':');
    if (colonIndex > 0) {
      String filename = header.substring(0, colonIndex);
      long filesize = header.substring(colonIndex + 1).toInt();

      String fullPath = "/" + filename;
      Serial.printf("[RECEIVER] Nhận header. File: %s, Kích thước: %ld bytes\n", fullPath.c_str(), filesize);

      File audioFile = SPIFFS.open(fullPath, FILE_WRITE);
      if (!audioFile) {
        Serial.println("[ERROR] Không thể tạo file trên SPIFFS!");
        client.stop();
        return;
      }

      uint8_t buffer[1024];
      long bytesReceived = 0;
      Serial.print("[RECEIVING] Đang nhận file... ");

      while (bytesReceived < filesize) {
        int len = client.read(buffer, sizeof(buffer));
        if (len > 0) {
          audioFile.write(buffer, len);
          bytesReceived += len;
        }
      }

      audioFile.close();
      Serial.printf("Hoàn tất! Đã nhận %ld bytes.\n", bytesReceived);

      filenameToPlay = filename;
      playRequest = true;
    } else {
      Serial.println("[ERROR] Header không hợp lệ.");
    }

    client.stop();
    Serial.println("[SERVER] Client đã ngắt kết nối.");
  }
}

void setupI2S_Microphone() { // *** SỬA LỖI: Đổi tên hàm cho rõ ràng ***
  i2s_config_t cfg = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = (i2s_comm_format_t)(I2S_COMM_FORMAT_I2S | I2S_COMM_FORMAT_I2S_MSB),
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 6,
    .dma_buf_len = 256,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };

  i2s_pin_config_t pin = {
    .bck_io_num = I2S_SCK,
    .ws_io_num = I2S_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_SD
  };

  // Cài đặt driver cho I2S Port 0 (Microphone)
  i2s_driver_install(I2S_NUM_0, &cfg, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &pin);
  i2s_zero_dma_buffer(I2S_NUM_0);
}

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 + INMP441 UDP Audio Streaming + LED Control + TCP Player");

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Đang kết nối WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println("\nWiFi đã kết nối!");
  Serial.println("IP: " + WiFi.localIP().toString());

  udp.begin(SERVER_PORT);
  cmdUdp.begin(COMMAND_PORT);

  if (!SPIFFS.begin(true)) {
    Serial.println("[ERROR] Không thể khởi tạo SPIFFS!");
  } else {
    Serial.println("[SETUP] SPIFFS đã sẵn sàng.");
  }

  server.begin();
  Serial.printf("[SETUP] TCP Server đã bắt đầu, đang chờ kết nối trên port %d\n", TCP_PORT);

  // *** SỬA LỖI: Khởi tạo AudioOutputI2S với port I2S_NUM_1 ***
  out = new AudioOutputI2S(I2S_PORT_PLAYER);
  out->SetPinout(I2S_BCLK_PIN, I2S_LRC_PIN, I2S_DOUT_PIN);

  // *** SỬA LỖI: Gọi hàm setup I2S cho micro ***
  setupI2S_Microphone();
  t0ms = millis();

  Serial.println("Hệ thống đã sẵn sàng streaming âm thanh + LED control!");
  Serial.printf("Sample rate: %d Hz, Frame: %d ms, Samples/frame: %d\n",
                SAMPLE_RATE, FRAME_MS, SAMPLES_PER_FR);
  Serial.printf("Kết nối tới server: %s:%d\n", SERVER_IP, SERVER_PORT);
  Serial.printf("Lắng nghe lệnh trên port: %d\n", COMMAND_PORT);
  Serial.println("Lệnh hỗ trợ: BLINK3, LED_GREEN_ON, LED_GREEN_OFF");

  Serial.println("💡 Test LED...");
  blinkLED(2);
}

// *** CHỈNH SỬA: Chỉ stream audio khi mic được bật ***
void loop() {
  handleCommand();
  handleAudioPlayback();
  handleTCPServer();

  // Chỉ thực hiện streaming khi mic đang được bật
  if (isMicStreaming) {
    // Phần streaming audio từ micro giữ nguyên
    int32_t raw32[SAMPLES_PER_FR];
    size_t bytesRead = 0;
    esp_err_t result = i2s_read(I2S_NUM_0, (void*)raw32, sizeof(raw32), &bytesRead, portMAX_DELAY);

    if (result != ESP_OK) {
      Serial.println("Lỗi đọc I2S!");
      delay(100);
      return;
    }

    int n32 = bytesRead / 4;
    if (n32 == 0) {
      delay(10);
      return;
    }

    static int16_t pcm16[SAMPLES_PER_FR];

    for (int i = 0; i < n32; i++) {
      pcm16[i] = (int16_t)(raw32[i] >> AUDIO_GAIN);
    }

    PacketHeader h;
    h.seq   = seq++;
    h.t_ms  = millis() - t0ms;
    h.codec = ENABLE_ULAW ? 1 : 0;
    write_len24(h, n32 * (ENABLE_ULAW ? 1 : 2));

    udp.beginPacket(SERVER_IP, SERVER_PORT);
    udp.write((uint8_t*)&h, sizeof(h));

    if (ENABLE_ULAW) {
      udp.write((uint8_t*)pcm16, n32 * 2);
    } else {
      udp.write((uint8_t*)pcm16, n32 * 2);
    }

    bool sent = udp.endPacket();

    if (sent) {
      if (seq % 50 == 0) {
        Serial.printf("Đã gửi %d gói, frame %d samples, codec: %s\n",
                      seq, n32, ENABLE_ULAW ? "μ-law" : "PCM16");
      }
    } else {
      Serial.println("Lỗi gửi UDP!");
    }

    delay(FRAME_MS);
  } else {
    // Khi mic tắt, chỉ cần một delay nhỏ để không khóa CPU
    delay(50);
  }
}