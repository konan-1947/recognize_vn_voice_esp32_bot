#ifndef SECRETS_H
#define SECRETS_H

// --- Thông tin Server (Fallback khi mDNS không hoạt động) ---
const char* SERVER_IP = "192.168.1.35"; // IP fallback của máy tính chạy server
const int SERVER_PORT = 5005;

// --- Cấu hình mDNS ---
const char* MDNS_HOSTNAME = "robot-server"; // Tên host để tìm kiếm qua mDNS

// --- Danh sách các mạng WiFi đã biết ---
const char* known_wifis[][2] = {
  { "Hồng Anh", "0915597079" },
  { "Thai Binh 2", "0915597079" },
  { "Router1", "dangVuDinh" }
};

#endif