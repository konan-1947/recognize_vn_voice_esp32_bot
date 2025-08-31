#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDP Handler - Xử lý giao tiếp UDP với ESP32
"""

import socket
import struct
import time
import audio_utils.server_config as config

def send_led_command(command):
    """Gửi lệnh điều khiển LED đến ESP32"""
    if config.esp32_address is None:
        print("❌ Chưa biết địa chỉ ESP32, không thể gửi lệnh LED")
        return False
    
    try:
        # Tạo UDP socket để gửi lệnh
        cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Gửi lệnh đến ESP32
        message = command.encode('utf-8')
        cmd_socket.sendto(message, (config.esp32_address[0], config.COMMAND_PORT))
        cmd_socket.close()
        
        print(f"✅ Đã gửi lệnh '{command}' đến ESP32 ({config.esp32_address[0]}:{config.COMMAND_PORT})")
        return True
    except Exception as e:
        print(f"❌ Lỗi gửi lệnh LED: {e}")
        return False

def udp_listener():
    """Thread lắng nghe UDP audio từ ESP32"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((config.HOST, config.UDP_PORT))
    print(f"🎧 UDP Audio server đang lắng nghe trên {config.HOST}:{config.UDP_PORT}")
    print(f"📡 Đang chờ audio packets từ ESP32...")
    
    packet_count = 0
    
    while not config.shutdown_event.is_set():
        try:
            # Set timeout để có thể kiểm tra shutdown event
            sock.settimeout(1.0)
            data, addr = sock.recvfrom(2048)
            packet_count += 1
            
            # Cập nhật địa chỉ ESP32 lần đầu tiên nhận data
            if config.esp32_address is None or config.esp32_address[0] != addr[0]:
                config.esp32_address = addr
                print(f"📡 Đã ghi nhận địa chỉ ESP32: {addr[0]}:{addr[1]}")
            
            if packet_count % 500 == 0:  # Log mỗi 500 packets
                print(f"📦 Nhận {packet_count} packets từ {addr}")
            
            if len(data) <= 12: 
                continue
                
            # Parse header ESP32: seq(4) + time_ms(4) + codec(1) + len24(3)
            try:
                seq, time_ms, codec, len_b2, len_b1, len_b0 = struct.unpack_from("<IIBBBB", data, 0)
                length = (len_b2 << 16) | (len_b1 << 8) | len_b0
                payload = data[12:12+length]
                
                if len(payload) == length:
                    config.q_audio.append((payload, time_ms, seq))
                    
            except struct.error as e:
                # Nếu không parse được header, coi như raw audio
                config.q_audio.append((data, int(time.time() * 1000), 0))
                
        except socket.timeout:
            # Timeout, kiểm tra shutdown event
            continue
        except Exception as e:
            if not config.shutdown_event.is_set():
                print(f"❌ Lỗi UDP listener: {e}")
            continue
    
    print("🛑 UDP Listener đã dừng")
    sock.close()