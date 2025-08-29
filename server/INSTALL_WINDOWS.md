# 🪟 Hướng dẫn cài đặt trên Windows

Hướng dẫn chi tiết để cài đặt và chạy dự án ESP32 + INMP441 Voice Recognition Server trên Windows.

## 📋 Yêu cầu hệ thống

- **OS**: Windows 10/11 (64-bit)
- **Python**: 3.7 hoặc cao hơn
- **RAM**: Tối thiểu 4GB (khuyến nghị 8GB+)
- **Storage**: Tối thiểu 2GB trống
- **Network**: Kết nối internet ổn định
- **Firewall**: Cần cấu hình để cho phép ports 5000 và 5005

## 🚀 Cài đặt nhanh

### 1. Cài đặt Python
- Tải Python từ [python.org](https://www.python.org/downloads/)
- Chọn "Add Python to PATH" khi cài đặt
- Chọn "Install for all users" (khuyến nghị)

### 2. Cài đặt Git
- Tải Git từ [git-scm.com](https://git-scm.com/download/win)
- Sử dụng cài đặt mặc định

### 3. Clone và cài đặt dự án
```cmd
cd C:\
git clone <repository-url>
cd test_voice2\server
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 🔧 Cài đặt chi tiết

### Bước 1: Chuẩn bị hệ thống

#### Cài đặt Python
1. Tải Python 3.8+ từ [python.org](https://www.python.org/downloads/)
2. Chạy installer với quyền Administrator
3. **Quan trọng**: Chọn "Add Python to PATH"
4. Chọn "Install for all users"
5. Chọn "Customize installation"
6. Chọn tất cả optional features
7. Chọn "Install for all users" trong Advanced Options

#### Cài đặt Git
1. Tải Git từ [git-scm.com](https://git-scm.com/download/win)
2. Chạy installer với quyền Administrator
3. Sử dụng cài đặt mặc định
4. Chọn "Git from the command line and also from 3rd-party software"

#### Cài đặt Visual Studio Build Tools (nếu cần)
```cmd
# Nếu gặp lỗi khi cài đặt numpy
winget install Microsoft.VisualStudio.2022.BuildTools
# Hoặc tải từ Microsoft Store
```

### Bước 2: Cài đặt dự án

#### Clone repository
```cmd
cd C:\
git clone <repository-url>
cd test_voice2\server
```

#### Tạo virtual environment
```cmd
python -m venv venv
venv\Scripts\activate
```

#### Cài đặt dependencies
```cmd
# Cập nhật pip
python -m pip install --upgrade pip

# Cài đặt dependencies
pip install -r requirements.txt
```

### Bước 3: Cấu hình Windows

#### Cấu hình Firewall
1. Mở "Windows Defender Firewall with Advanced Security"
2. Chọn "Inbound Rules" → "New Rule"
3. Chọn "Port" → "Next"
4. Chọn "TCP" và nhập "5000" → "Next"
5. Chọn "Allow the connection" → "Next"
6. Chọn tất cả profiles → "Next"
7. Đặt tên "Voice Recognition HTTP" → "Finish"
8. Lặp lại cho UDP port 5005

#### Cấu hình Antivirus
- Thêm thư mục `C:\test_voice2` vào whitelist
- Tạm thời disable real-time protection nếu cần

#### Cấu hình Network
```cmd
# Kiểm tra ports
netstat -an | findstr :5000
netstat -an | findstr :5005

# Kiểm tra firewall rules
netsh advfirewall firewall show rule name="Voice Recognition HTTP"
netsh advfirewall firewall show rule name="Voice Recognition UDP"
```

## 🧪 Kiểm tra cài đặt

### 1. Kiểm tra Python
```cmd
python --version
pip --version
```

### 2. Kiểm tra dependencies
```cmd
cd C:\test_voice2\server
venv\Scripts\activate
python -c "import flask, flask_socketio, speech_recognition, numpy; print('✅ Tất cả dependencies đã được cài đặt')"
```

### 3. Test server
```cmd
cd C:\test_voice2\server
venv\Scripts\activate
python google_speech_circular_server.py
```

## 🔍 Troubleshooting Windows

### Lỗi "python is not recognized"
```cmd
# Kiểm tra PATH
echo %PATH%

# Thêm Python vào PATH thủ công
setx PATH "%PATH%;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python39"
setx PATH "%PATH%;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python39\Scripts"
```

### Lỗi pip install
```cmd
# Cập nhật pip
python -m pip install --upgrade pip

# Cài đặt wheel
pip install wheel

# Cài đặt từ source nếu cần
pip install --no-binary :all: numpy
```

### Lỗi Visual C++ compiler
```cmd
# Cài đặt Visual Studio Build Tools
winget install Microsoft.VisualStudio.2022.BuildTools

# Hoặc cài đặt pre-compiled wheels
pip install --only-binary :all: numpy
```

### Lỗi firewall
```cmd
# Tạo firewall rules bằng command line
netsh advfirewall firewall add rule name="Voice Recognition HTTP" dir=in action=allow protocol=TCP localport=5000
netsh advfirewall firewall add rule name="Voice Recognition UDP" dir=in action=allow protocol=UDP localport=5005
```

### Lỗi permissions
```cmd
# Chạy Command Prompt với quyền Administrator
# Hoặc thay đổi quyền thư mục
icacls "C:\test_voice2" /grant Users:F /T
```

## 🚀 Chạy server

### Khởi động server
```cmd
cd C:\test_voice2\server
venv\Scripts\activate
python google_speech_circular_server.py
```

### Chạy trong background
```cmd
cd C:\test_voice2\server
venv\Scripts\activate
start /B python google_speech_circular_server.py > server.log 2>&1
```

### Tạo batch file
Tạo file `start_server.bat`:
```batch
@echo off
cd /d C:\test_voice2\server
call venv\Scripts\activate
python google_speech_circular_server.py
pause
```

## 📱 Tạo Windows Service (tùy chọn)

### Sử dụng NSSM
```cmd
# Tải NSSM từ https://nssm.cc/
# Cài đặt service
nssm install VoiceRecognition "C:\test_voice2\server\venv\Scripts\python.exe" "C:\test_voice2\server\google_speech_circular_server.py"
nssm set VoiceRecognition AppDirectory "C:\test_voice2\server"
nssm set VoiceRecognition AppEnvironmentExtra "PATH=C:\test_voice2\server\venv\Scripts"

# Khởi động service
nssm start VoiceRecognition
nssm status VoiceRecognition
```

### Sử dụng Task Scheduler
1. Mở "Task Scheduler"
2. "Create Basic Task"
3. Đặt tên "Voice Recognition Server"
4. Chọn "When the computer starts"
5. Action: Start a program
6. Program: `C:\test_voice2\server\venv\Scripts\python.exe`
7. Arguments: `C:\test_voice2\server\google_speech_circular_server.py`
8. Start in: `C:\test_voice2\server`

## 🔒 Bảo mật

### Tạo user riêng
1. Mở "Computer Management" → "Local Users and Groups"
2. Tạo user mới "voiceuser"
3. Thêm vào group "Users"
4. Đặt password mạnh

### Cấu hình UAC
1. Mở "User Account Control Settings"
2. Đặt level phù hợp (khuyến nghị: Default)

### Cấu hình Windows Defender
1. Mở "Windows Security"
2. "Virus & threat protection" → "Manage settings"
3. Thêm thư mục `C:\test_voice2` vào exclusions

## 📊 Monitoring

### Performance Monitor
1. Mở "Performance Monitor"
2. Thêm counters: CPU, Memory, Network
3. Tạo Data Collector Set

### Event Viewer
1. Mở "Event Viewer"
2. Kiểm tra "Windows Logs" → "Application"
3. Tìm events liên quan đến Python

### Resource Monitor
1. Mở "Resource Monitor"
2. Monitor CPU, Memory, Disk, Network usage

## 🎯 Tối ưu hóa

### Tăng file handles
```cmd
# Tạo registry key
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Kernel" /v "ObCaseInsensitive" /t REG_DWORD /d 1 /f
```

### Tối ưu Python
```cmd
# Trong virtual environment
pip install --upgrade pip setuptools wheel
pip install --upgrade numpy
```

### Tối ưu Windows
1. Disable unnecessary services
2. Tăng virtual memory
3. Defragment disk (nếu cần)

## 🔧 Công cụ hữu ích

### Development
- **VS Code**: Code editor với Python support
- **PyCharm**: Python IDE chuyên nghiệp
- **Anaconda**: Python distribution với nhiều packages

### Monitoring
- **Process Explorer**: Advanced task manager
- **Wireshark**: Network protocol analyzer
- **Process Monitor**: File and registry monitoring

### Utilities
- **7-Zip**: File compression
- **Notepad++**: Text editor
- **WinSCP**: SFTP client

---

**Chúc bạn cài đặt thành công trên Windows! 🪟✨** 