#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prompt Manager - Quản lý system prompt từ file txt
Cho phép upload và quản lý các file prompt khác nhau
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional
from audio_utils.gemini_api import load_system_prompt_from_file, reset_system_prompt

class PromptManager:
    def __init__(self, prompts_dir: str = "prompts"):
        """
        Khởi tạo Prompt Manager
        
        Args:
            prompts_dir (str): Thư mục chứa các file prompt
        """
        self.base_dir = Path(__file__).parent
        self.prompts_dir = self.base_dir / prompts_dir
        self.prompts_dir.mkdir(exist_ok=True)
        
    def list_prompts(self) -> List[str]:
        """Liệt kê tất cả file prompt có sẵn"""
        try:
            prompt_files = []
            for file_path in self.prompts_dir.glob("*.txt"):
                prompt_files.append(file_path.name)
            return sorted(prompt_files)
        except Exception as e:
            print(f"Lỗi khi liệt kê prompt files: {e}")
            return []
    
    def upload_prompt(self, source_path: str, prompt_name: str = None) -> bool:
        """
        Upload file prompt từ đường dẫn khác vào thư mục prompts
        
        Args:
            source_path (str): Đường dẫn file nguồn
            prompt_name (str): Tên file đích (không bao gồm .txt)
            
        Returns:
            bool: True nếu thành công
        """
        try:
            source = Path(source_path)
            if not source.exists():
                print(f"File không tồn tại: {source_path}")
                return False
            
            # Tạo tên file đích
            if prompt_name:
                dest_name = f"{prompt_name}.txt"
            else:
                dest_name = source.name
                if not dest_name.endswith('.txt'):
                    dest_name += '.txt'
            
            dest_path = self.prompts_dir / dest_name
            
            # Copy file
            shutil.copy2(source, dest_path)
            print(f"✅ Đã upload prompt: {dest_name}")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi khi upload prompt: {e}")
            return False
    
    def load_prompt(self, prompt_name: str) -> bool:
        """
        Load prompt từ file trong thư mục prompts
        
        Args:
            prompt_name (str): Tên file prompt (có thể có hoặc không có .txt)
            
        Returns:
            bool: True nếu thành công
        """
        try:
            # Thêm .txt nếu chưa có
            if not prompt_name.endswith('.txt'):
                prompt_name += '.txt'
            
            prompt_path = self.prompts_dir / prompt_name
            
            if not prompt_path.exists():
                print(f"❌ File prompt không tồn tại: {prompt_name}")
                return False
            
            # Load prompt vào gemini_api
            success = load_system_prompt_from_file(str(prompt_path))
            if success:
                print(f"✅ Đã load prompt: {prompt_name}")
            return success
            
        except Exception as e:
            print(f"❌ Lỗi khi load prompt: {e}")
            return False
    
    def view_prompt(self, prompt_name: str) -> Optional[str]:
        """
        Xem nội dung của một prompt file
        
        Args:
            prompt_name (str): Tên file prompt
            
        Returns:
            Optional[str]: Nội dung file hoặc None nếu lỗi
        """
        try:
            if not prompt_name.endswith('.txt'):
                prompt_name += '.txt'
            
            prompt_path = self.prompts_dir / prompt_name
            
            if not prompt_path.exists():
                print(f"❌ File prompt không tồn tại: {prompt_name}")
                return None
            
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return content
            
        except Exception as e:
            print(f"❌ Lỗi khi đọc prompt: {e}")
            return None
    
    def delete_prompt(self, prompt_name: str) -> bool:
        """
        Xóa một prompt file
        
        Args:
            prompt_name (str): Tên file prompt
            
        Returns:
            bool: True nếu thành công
        """
        try:
            if not prompt_name.endswith('.txt'):
                prompt_name += '.txt'
            
            prompt_path = self.prompts_dir / prompt_name
            
            if not prompt_path.exists():
                print(f"❌ File prompt không tồn tại: {prompt_name}")
                return False
            
            prompt_path.unlink()
            print(f"✅ Đã xóa prompt: {prompt_name}")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi khi xóa prompt: {e}")
            return False
    
    def reset_to_default(self):
        """Reset về system prompt mặc định"""
        reset_system_prompt()
        print("✅ Đã reset về system prompt mặc định")


def main():
    """Demo và test các chức năng"""
    pm = PromptManager()
    
    print("=== PROMPT MANAGER DEMO ===")
    
    # Liệt kê prompts
    print("\n📋 Danh sách prompts hiện có:")
    prompts = pm.list_prompts()
    if prompts:
        for i, prompt in enumerate(prompts, 1):
            print(f"  {i}. {prompt}")
    else:
        print("  (Chưa có prompt nào)")
    
    # Copy file example vào thư mục prompts
    example_file = Path(__file__).parent / "system_prompt_example.txt"
    if example_file.exists():
        pm.upload_prompt(str(example_file), "default_assistant")
        print("\n✅ Đã copy file example vào thư mục prompts")
    
    # Test load prompt
    print("\n🔄 Test load prompt...")
    if pm.load_prompt("default_assistant"):
        print("✅ Load prompt thành công!")
    
    print("\n=== HƯỚNG DẪN SỬ DỤNG ===")
    print("1. Tạo file .txt chứa system prompt của bạn")
    print("2. Sử dụng pm.upload_prompt(đường_dẫn_file, tên_prompt)")
    print("3. Sử dụng pm.load_prompt(tên_prompt) để áp dụng")
    print("4. Sử dụng pm.reset_to_default() để về mặc định")


if __name__ == "__main__":
    main()
