#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transcript Logger Module
Ghi text nhận diện được ra file txt, mỗi lần detect sẽ xuống dòng mới
"""

import os
from datetime import datetime
from typing import Optional

class TranscriptLogger:
    """Logger để ghi transcriptions ra file txt"""
    
    def __init__(self, output_dir: str = "transcripts", filename: str = "transcript_log.txt"):
        """
        Khởi tạo TranscriptLogger
        
        Args:
            output_dir (str): Thư mục output (mặc định: "transcripts")
            filename (str): Tên file log (mặc định: "transcript_log.txt")
        """
        self.output_dir = output_dir
        self.filename = filename
        self.filepath = os.path.join(output_dir, filename)
        
        # Tạo thư mục output nếu chưa có
        os.makedirs(output_dir, exist_ok=True)
        
        # Tạo file nếu chưa có
        if not os.path.exists(self.filepath):
            self._create_header()
    
    def _create_header(self):
        """Tạo header cho file log"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write("=== TRANSCRIPT LOG ===\n")
                f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("Format: [Timestamp] Text\n")
                f.write("=" * 50 + "\n\n")
            print(f"📝 Đã tạo file transcript log: {self.filepath}")
        except Exception as e:
            print(f"❌ Lỗi tạo header: {e}")
    
    def log_transcript(self, text: str, timestamp: Optional[float] = None) -> bool:
        """
        Ghi text nhận diện được ra file
        
        Args:
            text (str): Text đã được nhận diện
            timestamp (float, optional): Timestamp (mặc định: thời gian hiện tại)
        
        Returns:
            bool: True nếu ghi thành công, False nếu thất bại
        """
        if not text or not text.strip():
            return False
        
        try:
            # Format timestamp
            if timestamp is None:
                timestamp = datetime.now().timestamp()
            
            # Chuyển timestamp thành datetime string
            dt = datetime.fromtimestamp(timestamp / 1000 if timestamp > 1000000000000 else timestamp)
            time_str = dt.strftime('%H:%M:%S')
            
            # Ghi vào file
            with open(self.filepath, 'a', encoding='utf-8') as f:
                f.write(f"[{time_str}] {text.strip()}\n")
            
            print(f"📝 Đã ghi transcript: {text[:50]}{'...' if len(text) > 50 else ''}")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi ghi transcript: {e}")
            return False
    
    def log_transcript_simple(self, text: str) -> bool:
        """
        Ghi text đơn giản (chỉ text, không có timestamp)
        
        Args:
            text (str): Text đã được nhận diện
        
        Returns:
            bool: True nếu ghi thành công, False nếu thất bại
        """
        if not text or not text.strip():
            return False
        
        try:
            with open(self.filepath, 'a', encoding='utf-8') as f:
                f.write(f"{text.strip()}\n")
            
            print(f"📝 Đã ghi transcript: {text[:50]}{'...' if len(text) > 50 else ''}")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi ghi transcript: {e}")
            return False
    
    def get_filepath(self) -> str:
        """Lấy đường dẫn file log"""
        return self.filepath
    
    def get_stats(self) -> dict:
        """Lấy thống kê file log"""
        try:
            if not os.path.exists(self.filepath):
                return {"lines": 0, "size_bytes": 0, "exists": False}
            
            with open(self.filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            size_bytes = os.path.getsize(self.filepath)
            
            return {
                "lines": len(lines),
                "size_bytes": size_bytes,
                "size_kb": size_bytes / 1024,
                "exists": True
            }
        except Exception as e:
            return {"error": str(e), "exists": False}
    
    def clear_log(self) -> bool:
        """Xóa toàn bộ log và tạo header mới"""
        try:
            self._create_header()
            print(f"🗑️ Đã xóa log và tạo header mới: {self.filepath}")
            return True
        except Exception as e:
            print(f"❌ Lỗi xóa log: {e}")
            return False
    
    def backup_log(self, backup_name: Optional[str] = None) -> bool:
        """
        Backup log file
        
        Args:
            backup_name (str, optional): Tên file backup (mặc định: tự động tạo)
        
        Returns:
            bool: True nếu backup thành công
        """
        try:
            if not os.path.exists(self.filepath):
                print("❌ Không có file log để backup")
                return False
            
            if backup_name is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"transcript_log_backup_{timestamp}.txt"
            
            backup_path = os.path.join(self.output_dir, backup_name)
            
            # Copy file
            import shutil
            shutil.copy2(self.filepath, backup_path)
            
            print(f"💾 Đã backup log: {backup_path}")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi backup log: {e}")
            return False 