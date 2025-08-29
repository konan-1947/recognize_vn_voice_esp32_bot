# 🔌 Cấu hình chân ESP32 + INMP441

Hướng dẫn chi tiết về cách kết nối chân giữa ESP32 và microphone INMP441 cho dự án Voice Recognition Server.

## 📋 Danh sách linh kiện

### Hardware cần thiết
- **ESP32**: ESP32-WROOM-32 hoặc tương tự
- **INMP441**: I2S MEMS Microphone
- **Breadboard**: Để test và prototype
- **Jumper wires**: Kết nối các chân
- **USB-C cable**: Cấp nguồn và upload code
- **Power supply**: 3.3V (có thể dùng USB)

### Linh kiện phụ (tùy chọn)
- **Capacitor**: 100nF ceramic (lọc nhiễu)
- **Resistor**: 10kΩ pull-up (nếu cần)
- **LED**: Để hiển thị trạng thái
- **Button**: Reset hoặc test

## 🔌 Sơ đồ kết nối chân

### ESP32 Pinout
```
ESP32-WROOM-32 Pinout:
┌─────────────────────────────────────────┐
│                                         │
│  GND  IO2  IO4  IO16  IO17  IO5  IO18 │
│  IO3  IO1  IO22 IO21  IO19 IO23 IO25  │
│  IO26 IO27 IO14 IO12 IO13 IO15 IO2    │
│  IO0  IO4  IO16 IO17 IO5  IO18 IO19  │
│  IO21 IO22 IO23 IO25 IO26 IO27 IO14  │
│  IO12 IO13 IO15 IO2  IO0  IO4  IO16  │
│  IO17 IO5  IO18 IO19 IO21 IO22 IO23  │
│  IO25 IO26 IO27 IO14 IO12 IO13 IO15  │
│                                         │
│  VIN  GND  GND  GND  GND  GND  GND   │
│  EN   IO36 IO39 IO34 IO35 IO32 IO33  │
│  IO25 IO26 IO27 IO14 IO12 IO13 IO15  │
│  IO4  IO16 IO17 IO5  IO18 IO19 IO21  │
│  IO22 IO23 IO25 IO26 IO27 IO14 IO12  │
│  IO13 IO15 IO2  IO0  IO4  IO16 IO17  │
│  IO5  IO18 IO19 IO21 IO22 IO23 IO25  │
│  IO26 IO27 IO14 IO12 IO13 IO15 IO2   │
└─────────────────────────────────────────┘
```

### INMP441 Pinout
```
INMP441 Pinout:
┌─────────────────┐
│                 │
│    ┌───────┐    │
│    │       │    │
│    │  INMP │    │
│    │  441  │    │
│    │       │    │
│    └───────┘    │
│                 │
│ 1 2 3 4 5 6    │
│                 │
└─────────────────┘

Chân 1: VDD (3.3V)
Chân 2: GND
Chân 3: SD (Serial Data)
Chân 4: L/R (Left/Right Channel)
Chân 5: WS (Word Select)
Chân 6: SCK (Serial Clock)
```

## 🔗 Kết nối chân chi tiết

### Kết nối cơ bản
```
ESP32          INMP441
┌─────┐        ┌─────┐
│     │        │     │
│ 3V3 ├────────┤ VDD │ (Chân 1)
│     │        │     │
│ GND ├────────┤ GND │ (Chân 2)
│     │        │     │
│ IO32├────────┤ SD  │ (Chân 3) - Serial Data
│     │        │     │
│ IO33├────────┤ L/R │ (Chân 4) - Channel Select
│     │        │     │
│ IO25├────────┤ WS  │ (Chân 5) - Word Select
│     │        │     │
│ IO26├────────┤ SCK │ (Chân 6) - Serial Clock
│     │        │     │
└─────┘        └─────┘
```

### Kết nối với breadboard
```
Breadboard Layout:
┌─────────────────────────────────────────────────┐
│                                                 │
│  ESP32    │  Jumper Wires  │  INMP441          │
│           │                 │                   │
│  3V3 ────┼─────────────────┼─── VDD (Chân 1)   │
│           │                 │                   │
│  GND ────┼─────────────────┼─── GND (Chân 2)   │
│           │                 │                   │
│  IO32 ───┼─────────────────┼─── SD  (Chân 3)   │
│           │                 │                   │
│  IO33 ───┼─────────────────┼─── L/R (Chân 4)   │
│           │                 │                   │
│  IO25 ───┼─────────────────┼─── WS  (Chân 5)   │
│           │                 │                   │
│  IO26 ───┼─────────────────┼─── SCK (Chân 6)   │
│           │                 │                   │
└─────────────────────────────────────────────────┘
```

## ⚡ Cấu hình nguồn

### Nguồn 3.3V
```
Power Supply Options:
┌─────────────────────────────────────────────────┐
│                                                 │
│  Option 1: USB Power (5V → 3.3V)               │
│  ┌─────┐    ┌─────┐    ┌─────┐                 │
│  │ USB │───▶│ ESP32│───▶│3.3V │                 │
│  │ 5V  │   │ LDO  │   │     │                 │
│  └─────┘   └─────┘   └─────┘                 │
│                                                 │
│  Option 2: External 3.3V Supply                │
│  ┌─────┐    ┌─────┐    ┌─────┐                 │
│  │3.3V │───▶│ ESP32│───▶│3.3V │                 │
│  │PSU  │   │      │   │     │                 │
│  └─────┘   └─────┘   └─────┘                 │
│                                                 │
│  Option 3: Battery (3.7V → 3.3V)               │
│  ┌─────┐    ┌─────┐    ┌─────┐                 │
│  │3.7V │───▶│ ESP32│───▶│3.3V │                 │
│  │LiPo │   │ LDO  │   │     │                 │
│  └─────┘   └─────┘   └─────┘                 │
└─────────────────────────────────────────────────┘
```

### Lọc nhiễu nguồn
```
Power Filtering:
┌─────────────────────────────────────────────────┐
│                                                 │
│  3.3V ──┬── 100nF ── GND                      │
│          │                                      │
│          └── INMP441 VDD                        │
│                                                 │
│  GND ──┬── 100nF ── 3.3V                      │
│         │                                      │
│         └── INMP441 GND                         │
└─────────────────────────────────────────────────┘
```

## 🔧 Cấu hình I2S

### I2S Pin Assignment
```cpp
// Trong test_voice2.ino
#define I2S_WS_PIN      25    // Word Select (WS)
#define I2S_SCK_PIN     26    // Serial Clock (SCK)
#define I2S_SD_PIN      32    // Serial Data (SD)
#define I2S_LR_PIN      33    // Left/Right Channel (L/R)
```

### I2S Configuration
```cpp
// I2S Configuration
const i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = 16000,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 1024,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
};
```

## 📐 Layout PCB (tùy chọn)

### Single-sided PCB Layout
```
PCB Layout (Top Layer):
┌─────────────────────────────────────────────────┐
│                                                 │
│  ┌─────────┐    ┌─────────┐                     │
│  │  ESP32  │    │ INMP441 │                     │
│  │         │    │         │                     │
│  │ 3V3 ───┼────┼─── VDD  │                     │
│  │ GND ───┼────┼─── GND  │                     │
│  │ IO32 ──┼────┼─── SD   │                     │
│  │ IO33 ──┼────┼─── L/R  │                     │
│  │ IO25 ──┼────┼─── WS   │                     │
│  │ IO26 ──┼────┼─── SCK  │                     │
│  │         │    │         │                     │
│  └─────────┘    └─────────┘                     │
│                                                 │
│  ┌─────────┐    ┌─────────┐                     │
│  │ 100nF   │    │ 100nF   │                     │
│  │ Cap     │    │ Cap     │                     │
│  └─────────┘    └─────────┘                     │
│                                                 │
│  ┌─────────┐    ┌─────────┐                     │
│  │ USB-C   │    │ LED     │                     │
│  │ Conn    │    │ Status  │                     │
│  └─────────┘    └─────────┘                     │
└─────────────────────────────────────────────────┘
```

### Component Placement
```
Component Placement Guide:
┌─────────────────────────────────────────────────┐
│                                                 │
│  Top Left:    ESP32                            │
│  Top Right:   INMP441                          │
│  Bottom Left: USB-C Connector                  │
│  Bottom Right: Status LED                      │
│  Center:      Decoupling Capacitors            │
│                                                 │
│  Trace Width: 0.5mm (signal), 1.0mm (power)    │
│  Via Size:    0.6mm                            │
│  Clearance:   0.3mm                            │
└─────────────────────────────────────────────────┘
```

## 🔍 Kiểm tra kết nối

### Test continuity
```bash
# Sử dụng multimeter để kiểm tra:
1. 3V3 → VDD: Điện áp 3.3V
2. GND → GND: Điện trở 0Ω
3. IO32 → SD: Điện trở thấp
4. IO33 → L/R: Điện trở thấp
5. IO25 → WS: Điện trở thấp
6. IO26 → SCK: Điện trở thấp
```

### Test I2S communication
```cpp
// Test code để kiểm tra I2S
void test_i2s_connection() {
    Serial.println("Testing I2S connection...");
    
    // Kiểm tra I2S driver
    if (i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL) != ESP_OK) {
        Serial.println("❌ I2S driver installation failed");
        return;
    }
    
    // Kiểm tra I2S port
    if (i2s_set_pin(I2S_NUM_0, &pin_config) != ESP_OK) {
        Serial.println("❌ I2S pin configuration failed");
        return;
    }
    
    Serial.println("✅ I2S connection test passed");
}
```

## 🚨 Lưu ý quan trọng

### Pin compatibility
- **ESP32**: Chỉ sử dụng chân 3.3V, không dùng 5V
- **INMP441**: Hoạt động ở 3.3V, không chịu được 5V
- **I2S pins**: Không được dùng cho mục đích khác

### Ground connection
- **Single ground**: Tất cả GND phải được kết nối
- **Ground loop**: Tránh tạo ground loop
- **Shielding**: Có thể dùng shield cho audio quality

### Power stability
- **Decoupling**: Sử dụng capacitor để lọc nhiễu
- **Current**: INMP441 cần ~1mA
- **Voltage**: 3.3V ±5% (3.135V - 3.465V)

## 🔧 Troubleshooting

### Không có audio
1. Kiểm tra kết nối chân
2. Kiểm tra nguồn 3.3V
3. Kiểm tra I2S configuration
4. Kiểm tra Serial Monitor

### Audio bị nhiễu
1. Thêm decoupling capacitors
2. Kiểm tra ground connection
3. Tránh chạy gần nguồn nhiễu
4. Sử dụng shielded cables

### ESP32 không khởi động
1. Kiểm tra USB cable
2. Kiểm tra nguồn cung cấp
3. Kiểm tra code upload
4. Kiểm tra Serial Monitor

## 📚 Tài liệu tham khảo

### Datasheets
- **ESP32**: [ESP32 Technical Reference Manual](https://www.espressif.com/sites/default/files/documentation/esp32_technical_reference_manual_en.pdf)
- **INMP441**: [INMP441 Datasheet](https://www.invensense.com/wp-content/uploads/2015/02/INMP441.pdf)

### I2S Documentation
- **ESP32 I2S**: [ESP32 I2S API Reference](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/i2s.html)
- **I2S Protocol**: [I2S Bus Specification](https://www.sparkfun.com/datasheets/BreakoutBoards/I2SBUS.pdf)

---

**Chúc bạn kết nối thành công! 🔌✨** 