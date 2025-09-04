// ===== ESP32 + INMP441 → UDP PCM16LE 16kHz mono + Animated Eyes =====
#include <WiFi.h>
#include <WiFiUdp.h>
#include "driver/i2s.h"
#include "config.h"  // File cấu hình WiFi và pins

// Thư viện cho audio playback
#include "SPIFFS.h"
#include "AudioFileSourceSPIFFS.h"
#include "AudioGeneratorWAV.h"
#include "AudioOutputI2S.h"

// Thư viện cho animated eyes
#include "engine/AnimationEngine.h"
#include "directors/Directors.h"
#include <U8g2lib.h>

// Thư viện cho đa nhiệm và WiFi
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <WiFiMulti.h>
#include <HTTPClient.h>
#include <ESPmDNS.h>
#include "secrets.h"

// Khởi tạo đối tượng màn hình OLED với pins mới (SDA=4, SCL=5)
U8G2_SSD1306_128X64_NONAME_F_SW_I2C u8g2(U8G2_R0, /* clock=*/ 5, /* data=*/ 4, /* reset=*/ U8X8_PIN_NONE);

// Task handle cho animation
TaskHandle_t animationTaskHandle = NULL;

// Biến cho animation và network
WiFiMulti wifiMulti;
String discovered_server_ip = "";
int discovered_server_port = 0;
bool server_discovered = false;

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
bool serverAvailable = false;
unsigned long lastServerCheck = 0;

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

// Hàm kiểm tra server có hoạt động không
bool checkServerAvailability() {
  WiFiUDP testUdp;
  testUdp.begin(0); // Port tạm thời
  
  // Gửi packet test nhỏ
  testUdp.beginPacket(SERVER_IP, SERVER_PORT);
  testUdp.write((const uint8_t*)"PING", 4);
  bool result = testUdp.endPacket();
  testUdp.stop();
  
  return result;
}

// =================================================================
// ANIMATION TASK - CHẠY TRÊN CORE 0 VỚI PRIORITY THẤP
// =================================================================
void animationTask(void* parameter) {
    Serial.println("[Animation Task] Bắt đầu animation task trên Core 0");
    
    while(1) {
        // 1. "Bộ não Chớp mắt" quyết định khi nào cần chớp
        if (blink_director_update()) {
            animation_engine_start_blink();
        }
        
        // 2. "Bộ não Cảm xúc" quyết định cảm xúc tiếp theo
        emotion_director_update();

        // 3. "Bộ não Hướng nhìn" quyết định khi nào cần liếc mắt
        gaze_director_update();

        // 4. Engine luôn cập nhật và vẽ lại mắt lên màn hình
        animation_engine_update();

        // Hiển thị thông báo trên OLED khi server không có sẵn
        if (!serverAvailable && isMicStreaming) {
            static unsigned long lastOledUpdate = 0;
            unsigned long currentTime = millis();
            if (currentTime - lastOledUpdate > 2000) {
                u8g2.clearBuffer();
                u8g2.setFont(u8g2_font_ncenB08_tr);
                u8g2.drawStr(10, 20, "Server offline");
                u8g2.drawStr(10, 35, SERVER_IP);
                u8g2.drawStr(10, 50, "Waiting...");
                u8g2.sendBuffer();
                lastOledUpdate = currentTime;
            }
        }
        
        // 30Hz - giảm tần số để tiết kiệm CPU cho audio
        vTaskDelay(33 / portTICK_PERIOD_MS);
    }
}

// =================================================================
// HÀM HELPER ĐỂ TÌM EMOTION THEO TÊN
// =================================================================
const Emotion* find_emotion_by_name(const char* emotion_name) {
    for (int i = 0; i < EMOTION_COUNT; i++) {
        if (strcmp(emotions[i].name, emotion_name) == 0) {
            return &emotions[i];
        }
    }
    return nullptr; // Không tìm thấy
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

// =================================================================
// TASK CHO CORE 0: XỬ LÝ MẠNG VÀ LOGIC "NÃO"
// =================================================================
void networkAndBrainTask(void *pvParameters) {
  Serial.println("Task Mạng & Não bộ đã bắt đầu trên Core 0.");

  // --- Bước 1: Kết nối WiFi ---
  int num_known_wifis = sizeof(known_wifis) / sizeof(known_wifis[0]);
  for (int i = 0; i < num_known_wifis; i++) {
      wifiMulti.addAP(known_wifis[i][0], known_wifis[i][1]);
  }

  Serial.println("[Core 0] Đang quét và kết nối WiFi...");
  while (wifiMulti.run() != WL_CONNECTED) {
      vTaskDelay(pdMS_TO_TICKS(1000)); // Dùng vTaskDelay thay cho delay()
      Serial.print(".");
  }
  Serial.println("\n[Core 0] KẾT NỐI WIFI THÀNH CÔNG!");
  Serial.print("[Core 0] Đã kết nối tới mạng: ");
  Serial.println(WiFi.SSID());
  Serial.print("[Core 0] Địa chỉ IP của ESP32: ");
  Serial.println(WiFi.localIP());

  // =================================================================
  // --- KHỞI TẠO mDNS VÀ TÌM SERVER ---
  // =================================================================
  Serial.println("\n[Core 0] Đang khởi tạo mDNS...");
  if (!MDNS.begin("robot-server")) {
    Serial.println("[Core 0] Lỗi khởi tạo mDNS!");
  } else {
    Serial.println("[Core 0] mDNS đã khởi tạo thành công!");
    
    // Tìm server bằng mDNS
    Serial.printf("[Core 0] Đang tìm '%s.local' trên mạng...\n", MDNS_HOSTNAME);
    
    // Thử tìm server trong 10 giây
    int attempts = 0;
    while (!server_discovered && attempts < 20) {
      int n = MDNS.queryService("http", "tcp");
      if (n > 0) {
        Serial.printf("[Core 0] Tìm thấy %d dịch vụ HTTP\n", n);
        
        for (int i = 0; i < n; ++i) {
          String hostname = MDNS.hostname(i);
          int port = MDNS.port(i);
          
          Serial.printf("[Core 0] Dịch vụ %d: %s (Port: %d)\n", i + 1, hostname.c_str(), port);
          
          // Kiểm tra xem có phải server của chúng ta không
          if (hostname.indexOf(MDNS_HOSTNAME) != -1) {
            // Lấy IP bằng cách resolve hostname
            IPAddress ip = MDNS.queryHost(hostname, 1000);
            if (ip.toString() != "0.0.0.0") {
              discovered_server_ip = ip.toString();
              discovered_server_port = port;
              server_discovered = true;
              
              Serial.println("[Core 0] 🎯 ĐÃ TÌM THẤY SERVER ROBOT!");
              Serial.printf("[Core 0] IP: %s, Port: %d\n", discovered_server_ip.c_str(), discovered_server_port);
              break;
            }
          }
        }
      }
      
      if (!server_discovered) {
        Serial.printf("[Core 0] Lần thử %d/20: Không tìm thấy server, thử lại sau 500ms...\n", attempts + 1);
        vTaskDelay(pdMS_TO_TICKS(500));
        attempts++;
      }
    }
    
    if (!server_discovered) {
      Serial.println("[Core 0] ⚠️ Không tìm thấy server qua mDNS, sử dụng IP cố định");
      discovered_server_ip = String(SERVER_IP);
      discovered_server_port = SERVER_PORT;
    }
  }

  // =================================================================
  // --- GỬI REQUEST KIỂM TRA ĐẾN SERVER ---
  // =================================================================
  Serial.println("\n[Core 0] Đang thử gửi request kiểm tra đến server...");
  
  HTTPClient http;
  String serverUrl = "http://" + discovered_server_ip + ":" + String(discovered_server_port) + "/";
  
  http.begin(serverUrl);
  int httpCode = http.GET();

  if (httpCode > 0) {
    String payload = http.getString();
    Serial.printf("[Core 0] Server đã phản hồi! Mã: %d\n", httpCode);
    Serial.println("[Core 0] Nội dung phản hồi:");
    Serial.println(payload);
  } else {
    Serial.printf("[Core 0] Lỗi kết nối đến server! Mã lỗi: %s\n", http.errorToString(httpCode).c_str());
  }
  http.end();
  // =================================================================
  // --- KẾT THÚC PHẦN THÊM MỚI ---
  // =================================================================

  // --- Bước 2: Vòng lặp chính của Core 0 ---
  // Vòng lặp này sẽ xử lý logic nặng và giao tiếp với server
  unsigned long lastHeartbeat = 0;
  unsigned long lastEmotionCheck = 0;
  
  for (;;) {
    unsigned long currentTime = millis();
    
    // Kiểm tra và duy trì kết nối WiFi
    if (wifiMulti.run() != WL_CONNECTED) {
        Serial.println("[Core 0] Mất kết nối WiFi! Đang thử kết nối lại...");
        // wifiMulti.run() sẽ tự động xử lý việc kết nối lại
    } else {
        // =================================================================
        // --- GỬI HEARTBEAT ĐỊNH KỲ (MỖI 5 GIÂY) ---
        // =================================================================
        if (currentTime - lastHeartbeat > 5000) {
            HTTPClient http;
            String heartbeatUrl = "http://" + discovered_server_ip + ":" + String(discovered_server_port) + "/api/heartbeat";
            
            http.begin(heartbeatUrl);
            http.addHeader("Content-Type", "application/json");
            
            // Tạo JSON payload cho heartbeat
            String jsonPayload = "{\"status\":\"alive\",\"free_heap\":" + String(esp_get_free_heap_size()) + "}";
            
            int httpCode = http.POST(jsonPayload);
            if (httpCode > 0) {
                Serial.printf("[Core 0] Heartbeat gửi thành công! Mã: %d\n", httpCode);
            } else {
                Serial.printf("[Core 0] Lỗi gửi heartbeat: %s\n", http.errorToString(httpCode).c_str());
            }
            http.end();
            
            lastHeartbeat = currentTime;
        }
        
        // =================================================================
        // --- KIỂM TRA LỆNH CẢM XÚC (MỖI 2 GIÂY) ---
        // =================================================================
        if (currentTime - lastEmotionCheck > 2000) {
            HTTPClient http;
            String emotionUrl = "http://" + discovered_server_ip + ":" + String(discovered_server_port) + "/api/emotion/next";
            
            http.begin(emotionUrl);
            int httpCode = http.GET();
            
            if (httpCode == 200) {
                String payload = http.getString();
                Serial.println("[Core 0] Nhận được lệnh cảm xúc:");
                Serial.println(payload);
                
                // Parse JSON để lấy emotion
                if (payload.indexOf("\"emotion\"") != -1) {
                    // Tìm emotion trong JSON
                    int startPos = payload.indexOf("\"emotion\":\"") + 11;
                    int endPos = payload.indexOf("\"", startPos);
                    if (startPos > 10 && endPos > startPos) {
                        String emotion = payload.substring(startPos, endPos);
                        Serial.printf("[Core 0] Thực hiện cảm xúc: %s\n", emotion.c_str());
                        
                        // Thực hiện thay đổi cảm xúc
                        const Emotion* target_emotion = find_emotion_by_name(emotion.c_str());
                        if (target_emotion != nullptr) {
                            // Lấy emotion hiện tại (neutral làm mặc định)
                            const Emotion* current_emotion = &emotions[NEUTRAL_STATE_INDEX];
                            
                            // Thực hiện animation chuyển đổi cảm xúc
                            animation_engine_change_emotion(
                                current_emotion,    // Từ cảm xúc hiện tại
                                target_emotion,     // Đến cảm xúc mới
                                1.0f,               // Thời gian chuyển đổi: 1 giây
                                1.0f,               // Cường độ: 100%
                                EASE_IN_OUT_QUAD,   // Kiểu easing
                                3000                // Thời gian giữ cảm xúc: 3 giây
                            );
                            
                            Serial.printf("[Core 0] Đã thực hiện cảm xúc: %s\n", emotion.c_str());
                        } else {
                            Serial.printf("[Core 0] Không tìm thấy cảm xúc: %s\n", emotion.c_str());
                        }
                    }
                }
            } else if (httpCode == 404) {
                // Không có lệnh cảm xúc mới
                // Serial.println("[Core 0] Không có lệnh cảm xúc mới");
            } else {
                Serial.printf("[Core 0] Lỗi kiểm tra cảm xúc: %s\n", http.errorToString(httpCode).c_str());
            }
            http.end();
            
            lastEmotionCheck = currentTime;
        }
    }

    // Tạm dừng task trong 100ms để không chiếm hết CPU của Core 0
    vTaskDelay(pdMS_TO_TICKS(100)); 
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
  Serial.println("ESP32 + INMP441 UDP Audio Streaming + LED Control + TCP Player + Animated Eyes");

  // Lấy hạt giống ngẫu nhiên từ phần cứng
  randomSeed(esp_random());

  // Khởi tạo màn hình OLED với pins mới
  u8g2.begin();
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_ncenB14_tr);
  u8g2.drawStr(10, 35, "Robot Eyes");
  u8g2.sendBuffer();
  
  // Khởi tạo animation system
  animation_engine_initialize();
  initialize_directors();

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  // WiFi sẽ được xử lý bởi Core 0 task
  // Giữ lại phần này để tương thích với audio streaming
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

  // Khởi tạo AudioOutputI2S với port I2S_NUM_1
  out = new AudioOutputI2S(I2S_PORT_PLAYER);
  out->SetPinout(I2S_BCLK_PIN, I2S_LRC_PIN, I2S_DOUT_PIN);

  // Gọi hàm setup I2S cho micro
  setupI2S_Microphone();
  t0ms = millis();

  // Tạo task cho Core 0 (Network + Brain)
  xTaskCreatePinnedToCore(
      networkAndBrainTask,   // Function to implement the task
      "NetworkBrain",        // Name of the task
      8192,                  // Stack size in words
      NULL,                  // Task input parameter
      2,                     // Priority of the task (0-25, cao hơn = ưu tiên hơn)
      NULL,                  // Task handle.
      0);                    // Core where the task should run (0)

  // Tạo animation task trên Core 0 với priority thấp
  xTaskCreatePinnedToCore(
      animationTask,         // Function to implement the task
      "Animation",           // Name of the task
      4096,                  // Stack size in words (nhỏ hơn)
      NULL,                  // Task input parameter
      1,                     // Priority = 1 (THẤP hơn network task)
      &animationTaskHandle,  // Task handle
      0);                    // Core 0 (cùng với network)

  Serial.println("Setup hoàn tất. Bắt đầu luồng chính trên Core 1...");
  Serial.println("ESP32 + INMP441 UDP Audio Streaming + LED Control + TCP Player + Animated Eyes!");
  Serial.printf("Sample rate: %d Hz, Frame: %d ms, Samples/frame: %d\n",
                SAMPLE_RATE, FRAME_MS, SAMPLES_PER_FR);
  Serial.printf("Kết nối tới server: %s:%d\n", SERVER_IP, SERVER_PORT);
  Serial.printf("Lắng nghe lệnh trên port: %d\n", COMMAND_PORT);
  Serial.println("Lệnh hỗ trợ: BLINK3, LED_GREEN_ON, LED_GREEN_OFF");

  Serial.println("Test LED...");
  blinkLED(2);
  
  Serial.println("Hàm setup() đã hoàn tất trên Core 1. Animation engine đang chạy.");
}


// *** LOOP CHÍNH TỐI ƯU CHO AUDIO VÀ ANIMATION ***
void loop() {
  // Core 1 bây giờ tập trung vào cả audio streaming và animation mượt mà
  
  // === PHẦN 1: XỬ LÝ AUDIO STREAMING (PRIORITY CAO) ===
  handleCommand();
  handleAudioPlayback();
  handleTCPServer();

  // Kiểm tra kết nối WiFi trước khi streaming
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected, attempting reconnection...");
    WiFi.reconnect();
    delay(1000);
    return;
  }

  // Kiểm tra server định kỳ (mỗi 10 giây)
  unsigned long currentTime = millis();
  if (currentTime - lastServerCheck > 10000) {
    serverAvailable = checkServerAvailability();
    lastServerCheck = currentTime;
    
    if (!serverAvailable) {
      Serial.printf("Server %s:%d không phản hồi. Tạm dừng streaming.\n", SERVER_IP, SERVER_PORT);
    } else {
      Serial.printf("Server %s:%d hoạt động bình thường.\n", SERVER_IP, SERVER_PORT);
    }
  }

  // AUDIO STREAMING - CHỈ KHI SERVER CÓ SẴN
  if (isMicStreaming && serverAvailable) {
    // Phần streaming audio từ micro
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

    // Gửi UDP với tối ưu tốc độ
    udp.beginPacket(SERVER_IP, SERVER_PORT);
    udp.write((uint8_t*)&h, sizeof(h));
    udp.write((uint8_t*)pcm16, n32 * 2);
    bool sent = udp.endPacket();

    // Debug UDP với thông tin chi tiết và xử lý lỗi
    if (!sent) {
      static uint32_t error_count = 0;
      error_count++;
      
      if (seq % 100 == 0) {
        Serial.printf("UDP Error at seq %d (errors: %d) - WiFi: %s, IP: %s, Port: %d\n", 
                      seq, error_count, WiFi.isConnected() ? "OK" : "FAIL", SERVER_IP, SERVER_PORT);
        
        // Kiểm tra và khởi tạo lại UDP nếu cần
        if (error_count > 50) {
          Serial.println("Too many UDP errors, reinitializing UDP...");
          udp.stop();
          delay(100);
          udp.begin(SERVER_PORT);
          error_count = 0;
        }
      }
      
      // Thêm delay nhỏ khi gửi thất bại để tránh spam
      delay(5);
    } else if (seq % 500 == 0) {
      Serial.printf("Audio streaming OK: %d packets sent\n", seq);
    }

    // Thêm delay nhỏ để tránh overload UDP buffer
    delayMicroseconds(500);
  } else {
    // Khi không streaming (server không có sẵn hoặc mic tắt)
    if (!serverAvailable && isMicStreaming) {
      // Hiển thị thông báo trên OLED khi server không có sẵn - COMMENTED FOR AUDIO DEBUG
      // static unsigned long lastOledUpdate = 0;
      // if (currentTime - lastOledUpdate > 2000) {
      //   u8g2.clearBuffer();
      //   u8g2.setFont(u8g2_font_ncenB08_tr);
      //   u8g2.drawStr(10, 20, "Server offline");
      //   u8g2.drawStr(10, 35, SERVER_IP);
      //   u8g2.drawStr(10, 50, "Waiting...");
      //   u8g2.sendBuffer();
      //   lastOledUpdate = currentTime;
      // }
    }
  }

  // === PHẦN 2: ANIMATION ĐÃ ĐƯỢC CHUYỂN SANG ANIMATION TASK TRÊN CORE 0 ===
  // Animation giờ chạy độc lập trên Core 0 với priority thấp
  // Core 1 chỉ tập trung vào audio streaming

  // Không delay khi streaming để đảm bảo realtime audio
  // Animation giờ chạy trên task riêng, không cần delay ở đây
  if (!isMicStreaming || !serverAvailable) {
    delay(5); // Delay rất nhỏ
  }
}