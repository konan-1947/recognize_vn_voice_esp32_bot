"""
Gemini API Simple Integration
============================

Module đơn giản để tích hợp Google Gemini AI API.
Chỉ cần một hàm để hỏi và nhận câu trả lời.

Cấu hình trong file .env:
    GEMINI_API_KEY=your_api_key_here
    GEMINI_SYSTEM_PROMPT=Your system prompt here

Sử dụng:
    from audio_utils.gemini_api import ask_gemini
    
    answer = ask_gemini("Thời tiết hôm nay thế nào?")
    print(answer)
"""

import os
import logging
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
    
try:
    from google import genai
except ImportError:
    genai = None

# Load environment variables from .env file
if load_dotenv:
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)

# Logger
logger = logging.getLogger(__name__)

# Global client instance
_client = None


def _get_client():
    """Lấy hoặc tạo Gemini client."""
    global _client
    
    if _client is None:
        if genai is None:
            raise ImportError("google-genai không được cài đặt. Chạy: pip install google-genai")
            
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY không được tìm thấy trong file .env. "
                "Vui lòng thêm GEMINI_API_KEY=your_api_key vào file .env"
            )
        
        # Set API key for genai client
        os.environ['GEMINI_API_KEY'] = api_key
        _client = genai.Client()
        logger.info("Gemini API client đã được khởi tạo")
    
    return _client


def ask_gemini(question: str) -> Optional[str]:
    """
    Hỏi Gemini AI và nhận câu trả lời.
    
    Args:
        question (str): Câu hỏi cần trả lời
        
    Returns:
        Optional[str]: Câu trả lời từ Gemini hoặc None nếu lỗi
    """
    if not question or not question.strip():
        logger.warning("Câu hỏi trống")
        return None
    
    try:
        # Get client
        client = _get_client()
        
        # Get system prompt from .env
        system_prompt = os.getenv('GEMINI_SYSTEM_PROMPT', 
                                 'Trả lời câu hỏi một cách ngắn gọn và chính xác bằng tiếng Việt.')
        
        # Create full prompt with system instruction
        full_prompt = f"{system_prompt}\n\nCâu hỏi: {question}"
        
        logger.debug(f"Đang gửi câu hỏi tới Gemini: {question[:50]}...")
        
        # Call Gemini API
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt
        )
        
        answer = response.text
        logger.info(f"Nhận được câu trả lời từ Gemini ({len(answer)} ký tự)")
        
        return answer
        
    except Exception as e:
        logger.error(f"Lỗi khi gọi Gemini API: {e}")
        return None


# Alias cho dễ sử dụng
gemini_ask = ask_gemini


