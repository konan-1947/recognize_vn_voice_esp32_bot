# 🐧 Hướng dẫn cài đặt trên Linux

Hướng dẫn chi tiết để cài đặt và chạy dự án ESP32 + INMP441 Voice Recognition Server trên Linux.

## 📋 Yêu cầu hệ thống

- **OS**: Ubuntu 18.04+, Debian 10+, CentOS 7+, hoặc tương tự
- **Python**: 3.7 hoặc cao hơn
- **RAM**: Tối thiểu 2GB (khuyến nghị 4GB+)
- **Storage**: Tối thiểu 1GB trống
- **Network**: Kết nối internet ổn định

## 🚀 Cài đặt nhanh (Ubuntu/Debian)

### 1. Cập nhật hệ thống
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Cài đặt Python và pip
```bash
sudo apt install python3 python3-pip python3-venv -y
```

### 3. Cài đặt system dependencies
```bash
sudo apt install build-essential python3-dev libasound2-dev portaudio19-dev -y
```

### 4. Clone và cài đặt dự án
```bash
cd ~
git clone <repository-url>
cd test_voice2/server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 🔧 Cài đặt chi tiết

### Bước 1: Chuẩn bị hệ thống

#### Ubuntu/Debian
```bash
# Cài đặt build tools
sudo apt update
sudo apt install -y build-essential python3-dev

# Cài đặt audio dependencies
sudo apt install -y libasound2-dev portaudio19-dev

# Cài đặt Python tools
sudo apt install -y python3 python3-pip python3-venv python3-dev
```

#### CentOS/RHEL/Fedora
```bash
# Cài đặt build tools
sudo yum groupinstall -y "Development Tools"
sudo yum install -y python3-devel

# Cài đặt audio dependencies
sudo yum install -y alsa-lib-devel portaudio-devel

# Cài đặt Python
sudo yum install -y python3 python3-pip python3-devel
```

#### Arch Linux
```bash
# Cài đặt build tools
sudo pacman -S base-devel

# Cài đặt audio dependencies
sudo pacman -S alsa-lib portaudio

# Cài đặt Python
sudo pacman -S python python-pip
```

### Bước 2: Cài đặt Python dependencies

```bash
# Tạo virtual environment
cd ~/test_voice2/server
python3 -m venv venv

# Kích hoạt virtual environment
source venv/bin/activate

# Cài đặt dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 3: Cấu hình firewall

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 5000/tcp  # Flask HTTP
sudo ufw allow 5005/udp  # ESP32 UDP
sudo ufw reload

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --permanent --add-port=5005/udp
sudo firewall-cmd --reload

# Arch Linux (iptables)
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 5005 -j ACCEPT
```

## 🧪 Kiểm tra cài đặt

### 1. Kiểm tra Python
```bash
python3 --version
pip --version
```

### 2. Kiểm tra dependencies
```bash
cd ~/test_voice2/server
source venv/bin/activate
python3 -c "import flask, flask_socketio, speech_recognition, numpy; print('✅ Tất cả dependencies đã được cài đặt')"
```

### 3. Test server
```bash
cd ~/test_voice2/server
source venv/bin/activate
python3 google_speech_circular_server.py
```

## 🔍 Troubleshooting Linux

### Lỗi PortAudio
```bash
# Ubuntu/Debian
sudo apt install -y portaudio19-dev

# CentOS/RHEL
sudo yum install -y portaudio-devel

# Arch Linux
sudo pacman -S portaudio
```

### Lỗi ALSA
```bash
# Cài đặt ALSA utilities
sudo apt install -y alsa-utils

# Kiểm tra audio devices
aplay -l
arecord -l
```

### Lỗi permissions
```bash
# Thêm user vào audio group
sudo usermod -a -G audio $USER

# Logout và login lại
# Hoặc restart system
```

### Lỗi Python version
```bash
# Cài đặt Python 3.8+ nếu cần
sudo apt install -y python3.8 python3.8-venv python3.8-dev

# Tạo virtual environment với Python 3.8
python3.8 -m venv venv
```

## 🚀 Chạy server

### Khởi động server
```bash
cd ~/test_voice2/server
source venv/bin/activate
python3 google_speech_circular_server.py
```

### Chạy trong background
```bash
cd ~/test_voice2/server
source venv/bin/activate
nohup python3 google_speech_circular_server.py > server.log 2>&1 &
```

### Kiểm tra status
```bash
# Kiểm tra process
ps aux | grep google_speech_circular_server

# Kiểm tra logs
tail -f server.log

# Kiểm tra ports
netstat -tulpn | grep :5000
netstat -tulpn | grep :5005
```

## 📱 Tạo systemd service (tùy chọn)

### Tạo service file
```bash
sudo nano /etc/systemd/system/voice-recognition.service
```

### Nội dung service file
```ini
[Unit]
Description=ESP32 Voice Recognition Server
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/test_voice2/server
Environment=PATH=/home/your_username/test_voice2/server/venv/bin
ExecStart=/home/your_username/test_voice2/server/venv/bin/python3 google_speech_circular_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Kích hoạt service
```bash
sudo systemctl daemon-reload
sudo systemctl enable voice-recognition.service
sudo systemctl start voice-recognition.service
sudo systemctl status voice-recognition.service
```

## 🔒 Bảo mật

### Tạo user riêng
```bash
# Tạo user mới
sudo adduser voiceuser
sudo usermod -a -G audio voiceuser

# Chuyển quyền sở hữu
sudo chown -R voiceuser:voiceuser ~/test_voice2
```

### Cấu hình firewall
```bash
# Chỉ cho phép IP cụ thể
sudo ufw allow from 192.168.1.0/24 to any port 5000
sudo ufw allow from 192.168.1.0/24 to any port 5005
```

## 📊 Monitoring

### Log rotation
```bash
sudo nano /etc/logrotate.d/voice-recognition
```

```conf
/home/your_username/test_voice2/server/server.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 your_username your_username
}
```

### Performance monitoring
```bash
# Monitor CPU và RAM
htop

# Monitor network
iftop

# Monitor disk I/O
iotop
```

## 🎯 Tối ưu hóa

### Tăng file descriptors
```bash
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
```

### Tối ưu Python
```bash
# Trong virtual environment
pip install --upgrade pip setuptools wheel
pip install --upgrade numpy
```

---

**Chúc bạn cài đặt thành công trên Linux! 🐧✨** 