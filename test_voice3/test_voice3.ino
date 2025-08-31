// ===== ESP32 + INMP441 → UDP PCM16LE 16kHz mono =====
#include <WiFi.h>
#include <WiFiUdp.h>
#include "driver/i2s.h"
#include "config.h"  // File cấu hình WiFi và pins

// ---- Audio params ----
#define SAMPLES_PER_FR  (SAMPLE_RATE * FRAME_MS / 1000)  // 320
#define BYTES_PER_SMP   2   // int16_t
#define FRAME_BYTES     (SAMPLES_PER_FR * BYTES_PER_SMP) // 640

// ---- LED Control ----
#define LED_BUILTIN 2  // Built-in LED trên GPIO 2
#define COMMAND_PORT 5006  // Port để nhận lệnh từ server

WiFiUDP udp;
WiFiUDP cmdUdp;  // UDP socket riêng để nhận lệnh
uint32_t seq = 0;
uint32_t t0ms = 0;

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
  /**
   * Bấm nhấp LED built-in một số lần nhất định
   */
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(200);  // Sáng 200ms
    digitalWrite(LED_BUILTIN, LOW);
    delay(200);  // Tắt 200ms
  }
}

void handleCommand() {
  /**
   * Xử lý lệnh nhận từ server
   */
  int packetSize = cmdUdp.parsePacket();
  if (packetSize > 0) {
    char commandBuffer[32];
    int len = cmdUdp.read(commandBuffer, sizeof(commandBuffer) - 1);
    commandBuffer[len] = '\0';  // Null-terminate string
    
    String command = String(commandBuffer);
    Serial.println("Nhận lệnh: " + command);
    
    if (command == "BLINK3") {
      Serial.println("💡 Thực hiện bấm nhấp LED 3 lần!");
      blinkLED(3);
    } else {
      Serial.println("Lệnh không hợp lệ: " + command);
    }
  }
}

void setupI2S() {
  i2s_config_t cfg = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT, // INMP441 out 24-bit ở khung 32-bit
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,  // đã kéo L/R về GND -> LEFT
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
    .data_out_num = I2S_PIN_NO_CHANGE, // mic -> RX nên không dùng TX
    .data_in_num = I2S_SD
  };

  i2s_driver_install(I2S_NUM_0, &cfg, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &pin);
  i2s_zero_dma_buffer(I2S_NUM_0);
}

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 + INMP441 UDP Audio Streaming + LED Control");
  
  // Khởi tạo LED
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  
  // Kết nối WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Đang kết nối WiFi");
  while (WiFi.status() != WL_CONNECTED) { 
    delay(300); 
    Serial.print("."); 
  }
  Serial.println("\nWiFi đã kết nối!");
  Serial.println("IP: " + WiFi.localIP().toString());

  // Khởi tạo UDP sockets
  udp.begin(SERVER_PORT); // optional, để có thể recv reply
  cmdUdp.begin(COMMAND_PORT); // Để nhận lệnh từ server
  
  setupI2S();
  t0ms = millis();
  
  Serial.println("Hệ thống đã sẵn sàng streaming âm thanh + LED control!");
  Serial.printf("Sample rate: %d Hz, Frame: %d ms, Samples/frame: %d\n", 
                SAMPLE_RATE, FRAME_MS, SAMPLES_PER_FR);
  Serial.printf("Kết nối tới server: %s:%d\n", SERVER_IP, SERVER_PORT);
  Serial.printf("Lắng nghe lệnh trên port: %d\n", COMMAND_PORT);
  
  // Test LED
  Serial.println("💡 Test LED...");
  blinkLED(2);
}

void loop() {
  // Xử lý lệnh từ server (kiểm tra trước)
  handleCommand();
  
  // Đọc 32-bit từ I2S, chuyển về int16_t (lấy 16 bit có nghĩa ở giữa)
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
    // INMP441: 24-bit hữu ích nằm ở 31..8 -> shift về 16-bit
    pcm16[i] = (int16_t)(raw32[i] >> AUDIO_GAIN); // Sử dụng AUDIO_GAIN từ config
  }

  // Gửi UDP
  PacketHeader h;
  h.seq   = seq++;
  h.t_ms  = millis() - t0ms;
  h.codec = ENABLE_ULAW ? 1 : 0; // Sử dụng cấu hình từ config
  write_len24(h, n32 * (ENABLE_ULAW ? 1 : 2)); // μ-law: 1 byte/sample, PCM: 2 bytes/sample

  udp.beginPacket(SERVER_IP, SERVER_PORT);
  udp.write((uint8_t*)&h, sizeof(h));
  
  if (ENABLE_ULAW) {
    // TODO: Thêm encoder μ-law ở đây
    udp.write((uint8_t*)pcm16, n32 * 2); // Tạm thời vẫn gửi PCM
  } else {
    udp.write((uint8_t*)pcm16, n32 * 2);
  }
  
  bool sent = udp.endPacket();
  
  if (sent) {
    // Hiển thị thông tin mỗi 50 gói để debug
    if (seq % 50 == 0) {
      Serial.printf("Đã gửi %d gói, frame %d samples, codec: %s\n", 
                    seq, n32, ENABLE_ULAW ? "μ-law" : "PCM16");
    }
  } else {
    Serial.println("Lỗi gửi UDP!");
  }
  
  // Đợi để đảm bảo frame 20ms
  delay(FRAME_MS);
}
