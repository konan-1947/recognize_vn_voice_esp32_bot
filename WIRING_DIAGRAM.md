# 🔌 Sơ đồ kết nối ESP32 + INMP441

Sơ đồ kết nối đơn giản và trực quan cho dự án Voice Recognition Server.

## 📍 Kết nối cơ bản

```
                    INMP441
                   ┌─────────┐
                   │         │
                   │  ┌───┐  │
                   │  │   │  │
                   │  │ M │  │
                   │  │ I │  │
                   │  │ C │  │
                   │  │   │  │
                   │  └───┘  │
                   │         │
                   │ 1 2 3 4 │
                   │ 5 6     │
                   └─────────┘
                        │
                        │
                    ┌───┴───┐
                    │       │
                    │ ESP32 │
                    │       │
                    └───────┘
```

## 🔗 Kết nối chi tiết

### Sơ đồ breadboard
```
Breadboard Layout:
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ESP32                    Jumper Wires              INMP441    │
│  ┌─────────┐                                              ┌─────┐ │
│  │         │                                              │     │ │
│  │ 3V3 ───┼──────────────────────────────────────────────┼─── 1│ │
│  │         │                                              │     │ │
│  │ GND ───┼──────────────────────────────────────────────┼─── 2│ │
│  │         │                                              │     │ │
│  │ IO32 ──┼──────────────────────────────────────────────┼─── 3│ │
│  │         │                                              │     │ │
│  │ IO33 ──┼──────────────────────────────────────────────┼─── 4│ │
│  │         │                                              │     │ │
│  │ IO25 ──┼──────────────────────────────────────────────┼─── 5│ │
│  │         │                                              │     │ │
│  │ IO26 ──┼──────────────────────────────────────────────┼─── 6│ │
│  │         │                                              │     │ │
│  └─────────┘                                              └─────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Sơ đồ chân
```
Pin Mapping:
┌─────────┬─────────┬─────────┬─────────┐
│ ESP32   │ Wire    │ INMP441 │ Function│
├─────────┼─────────┼─────────┼─────────┤
│ 3V3     │ Red     │ VDD (1) │ Power   │
│ GND     │ Black   │ GND (2) │ Ground  │
│ IO32    │ Blue    │ SD  (3) │ Data    │
│ IO33    │ Green   │ L/R (4) │ Channel │
│ IO25    │ Yellow  │ WS  (5) │ Select  │
│ IO26    │ Orange  │ SCK (6) │ Clock   │
└─────────┴─────────┴─────────┴─────────┘
```

## 🎨 Màu sắc dây (khuyến nghị)

### Màu chuẩn
```
Color Coding:
┌─────────┬─────────┬─────────┬─────────┐
│ Color   │ ESP32   │ INMP441 │ Purpose │
├─────────┼─────────┼─────────┼─────────┤
│ Red     │ 3V3     │ VDD (1) │ Power   │
│ Black   │ GND     │ GND (2) │ Ground  │
│ Blue    │ IO32    │ SD  (3) │ Data    │
│ Green   │ IO33    │ L/R (4) │ Channel │
│ Yellow  │ IO25    │ WS  (5) │ Select  │
│ Orange  │ IO26    │ SCK (6) │ Clock   │
└─────────┴─────────┴─────────┴─────────┘
```

### Màu thay thế
```
Alternative Colors:
┌─────────┬─────────┬─────────┬─────────┐
│ Color   │ ESP32   │ INMP441 │ Purpose │
├─────────┼─────────┼─────────┼─────────┤
│ White   │ 3V3     │ VDD (1) │ Power   │
│ Brown   │ GND     │ GND (2) │ Ground  │
│ Purple  │ IO32    │ SD  (3) │ Data    │
│ Gray    │ IO33    │ L/R (4) │ Channel │
│ Pink    │ IO25    │ WS  (5) │ Select  │
│ Cyan    │ IO26    │ SCK (6) │ Clock   │
└─────────┴─────────┴─────────┴─────────┘
```

## 🔌 Kết nối thực tế

### Bước 1: Chuẩn bị
```
1. Đặt ESP32 trên breadboard
2. Đặt INMP441 trên breadboard
3. Chuẩn bị 6 dây jumper
4. Đảm bảo breadboard có đủ hàng
```

### Bước 2: Kết nối nguồn
```
1. Kết nối 3V3 → VDD (chân 1)
2. Kết nối GND → GND (chân 2)
3. Kiểm tra đèn LED trên INMP441 sáng
```

### Bước 3: Kết nối I2S
```
1. Kết nối IO32 → SD (chân 3)
2. Kết nối IO33 → L/R (chân 4)
3. Kết nối IO25 → WS (chân 5)
4. Kết nối IO26 → SCK (chân 6)
```

## 📏 Khoảng cách và vị trí

### Vị trí lý tưởng
```
Breadboard Layout:
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌─────────┐                                              ┌─────┐ │
│  │  ESP32  │                                              │     │ │
│  │         │                                              │     │ │
│  │ 3V3 ───┼──────────────────────────────────────────────┼─── 1│ │
│  │         │                                              │     │ │
│  │ GND ───┼──────────────────────────────────────────────┼─── 2│ │
│  │         │                                              │     │ │
│  │ IO32 ──┼──────────────────────────────────────────────┼─── 3│ │
│  │         │                                              │     │ │
│  │ IO33 ──┼──────────────────────────────────────────────┼─── 4│ │
│  │         │                                              │     │ │
│  │ IO25 ──┼──────────────────────────────────────────────┼─── 5│ │
│  │         │                                              │     │ │
│  │ IO26 ──┼──────────────────────────────────────────────┼─── 6│ │
│  │         │                                              │     │ │
│  └─────────┘                                              └─────┘ │
│                                                                 │
│  ┌─────────┐                                              ┌─────┐ │
│  │ 100nF   │                                              │ LED │ │
│  │ Cap     │                                              │     │ │
│  └─────────┘                                              └─────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Khoảng cách tối ưu
```
Distance Guidelines:
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ESP32 ←── 2-3 cm ──→ INMP441                                 │
│                                                                 │
│  ┌─────────┐    ┌─────────┐                                    │
│  │         │    │         │                                    │
│  │  ESP32  │    │ INMP441 │                                    │
│  │         │    │         │                                    │
│  └─────────┘    └─────────┘                                    │
│                                                                 │
│  • Không quá gần: Tránh nhiễu điện từ                          │
│  • Không quá xa: Giảm điện trở dây                            │
│  • Khoảng cách lý tưởng: 2-3 cm                              │
└─────────────────────────────────────────────────────────────────┘
```

## 🔍 Kiểm tra kết nối

### Test trực quan
```
Visual Check:
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ✅ 3V3 → VDD: LED sáng                                        │
│  ✅ GND → GND: Điện áp 0V                                      │
│  ✅ IO32 → SD: Dây kết nối                                    │
│  ✅ IO33 → L/R: Dây kết nối                                   │
│  ✅ IO25 → WS: Dây kết nối                                    │
│  ✅ IO26 → SCK: Dây kết nối                                   │
│                                                                 │
│  ❌ Nếu LED không sáng: Kiểm tra nguồn                         │
│  ❌ Nếu có dây lỏng: Cắm lại                                   │
│  ❌ Nếu sai chân: Kiểm tra pinout                              │
└─────────────────────────────────────────────────────────────────┘
```

### Test bằng multimeter
```
Multimeter Test:
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Test 1: 3V3 → VDD                                            │
│  ┌─────┐    ┌─────┐                                           │
│  │ 3V3 │───▶│ VDD │ = 3.3V                                    │
│  └─────┘    └─────┘                                           │
│                                                                 │
│  Test 2: GND → GND                                            │
│  ┌─────┐    ┌─────┐                                           │
│  │ GND │───▶│ GND │ = 0V                                      │
│  └─────┘    └─────┘                                           │
│                                                                 │
│  Test 3: Continuity                                            │
│  ┌─────┐    ┌─────┐                                           │
│  │ IO32│───▶│ SD  │ = Beep (thông mạch)                       │
│  └─────┘    └─────┘                                           │
└─────────────────────────────────────────────────────────────────┘
```

## 🚨 Lưu ý quan trọng

### An toàn
```
Safety Guidelines:
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ⚠️  Không cắm/ngắt dây khi ESP32 đang hoạt động               │
│  ⚠️  Đảm bảo nguồn ổn định 3.3V                               │
│  ⚠️  Không để dây chạm vào nhau                                │
│  ⚠️  Kiểm tra kết nối trước khi bật nguồn                     │
│                                                                 │
│  ✅  Sử dụng dây có độ dài phù hợp                             │
│  ✅  Cắm dây chắc chắn vào breadboard                         │
│  ✅  Kiểm tra pinout trước khi kết nối                        │
│  ✅  Test từng kết nối một cách cẩn thận                       │
└─────────────────────────────────────────────────────────────────┘
```

### Chất lượng audio
```
Audio Quality Tips:
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  🎵 Sử dụng dây ngắn để giảm nhiễu                            │
│  🎵 Tránh đặt gần nguồn nhiễu (motor, transformer)            │
│  🎵 Sử dụng decoupling capacitors                              │
│  🎵 Đảm bảo ground connection tốt                             │
│  🎵 Tránh ground loop                                          │
│                                                                 │
│  📊 Chất lượng audio phụ thuộc vào:                           │
│     • Độ dài dây kết nối                                      │
│     • Vị trí đặt components                                   │
│     • Nguồn cung cấp ổn định                                  │
│     • Ground connection                                        │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Troubleshooting nhanh

### Vấn đề thường gặp
```
Common Issues:
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ❌ LED không sáng                                             │
│     → Kiểm tra nguồn 3.3V                                      │
│     → Kiểm tra kết nối GND                                     │
│                                                                 │
│  ❌ Không có audio                                             │
│     → Kiểm tra kết nối I2S pins                               │
│     → Kiểm tra code configuration                              │
│                                                                 │
│  ❌ Audio bị nhiễu                                             │
│     → Thêm decoupling capacitors                               │
│     → Kiểm tra ground connection                               │
│                                                                 │
│  ❌ ESP32 không khởi động                                      │
│     → Kiểm tra USB cable                                       │
│     → Kiểm tra nguồn cung cấp                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

**Chúc bạn kết nối thành công! 🔌✨** 