"""
Gemini API Enhanced Integration
===============================

Module nâng cao để tích hợp Google Gemini AI API với các tính năng:
- Giới hạn độ dài câu trả lời để tránh quá tải ESP32
- Ghi nhớ tên người dùng
- Đọc system prompt từ file txt
- Xử lý các tác vụ đặc biệt

Cấu hình trong file .env:
    GEMINI_API_KEY=your_api_key_here
    GEMINI_SYSTEM_PROMPT=Your system prompt here
    GEMINI_MAX_RESPONSE_LENGTH=200
    USER_MEMORY_FILE=user_memory.json

Sử dụng:
    from audio_utils.gemini_api import ask_gemini, load_system_prompt_from_file
    
    answer = ask_gemini("Thời tiết hôm nay thế nào?")
    load_system_prompt_from_file("my_prompt.txt")
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

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

# User memory storage
_user_memory = {}
_memory_file_path = None

# Conversation history storage
_conversation_history = []
_conversation_file_path = None

# Custom system prompt from file
_custom_system_prompt = None


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


def _load_user_memory():
    """Tải bộ nhớ người dùng từ file."""
    global _user_memory, _memory_file_path
    
    if _memory_file_path is None:
        memory_file = os.getenv('USER_MEMORY_FILE', 'user_memory.json')
        _memory_file_path = Path(__file__).parent.parent / memory_file
    
    try:
        if _memory_file_path.exists():
            with open(_memory_file_path, 'r', encoding='utf-8') as f:
                _user_memory = json.load(f)
            logger.info(f"Đã tải bộ nhớ người dùng từ {_memory_file_path}")
        else:
            _user_memory = {}
            logger.info("Tạo bộ nhớ người dùng mới")
    except Exception as e:
        logger.error(f"Lỗi khi tải bộ nhớ người dùng: {e}")
        _user_memory = {}

def _load_conversation_history():
    """Tải lịch sử 20 tin nhắn gần nhất từ file."""
    global _conversation_history, _conversation_file_path
    
    if _conversation_file_path is None:
        conversation_file = os.getenv('CONVERSATION_HISTORY_FILE', 'twenty_last_messages.json')
        _conversation_file_path = Path(__file__).parent.parent / conversation_file
    
    try:
        if _conversation_file_path.exists():
            with open(_conversation_file_path, 'r', encoding='utf-8') as f:
                _conversation_history = json.load(f)
            logger.info(f"Đã tải lịch sử hội thoại từ {_conversation_file_path} ({len(_conversation_history)} tin nhắn)")
        else:
            _conversation_history = []
            logger.info("Tạo lịch sử hội thoại mới")
    except Exception as e:
        logger.error(f"Lỗi khi tải lịch sử hội thoại: {e}")
        _conversation_history = []

def _save_user_memory():
    """Lưu bộ nhớ người dùng vào file."""
    global _user_memory, _memory_file_path
    
    try:
        if _memory_file_path:
            with open(_memory_file_path, 'w', encoding='utf-8') as f:
                json.dump(_user_memory, f, ensure_ascii=False, indent=2)
            logger.info(f"Đã lưu bộ nhớ người dùng vào {_memory_file_path}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu bộ nhớ người dùng: {e}")

def _save_conversation_history():
    """Lưu lịch sử hội thoại vào file."""
    global _conversation_history, _conversation_file_path
    
    try:
        if _conversation_file_path:
            with open(_conversation_file_path, 'w', encoding='utf-8') as f:
                json.dump(_conversation_history, f, ensure_ascii=False, indent=2)
            logger.info(f"Đã lưu lịch sử hội thoại vào {_conversation_file_path} ({len(_conversation_history)} tin nhắn)")
    except Exception as e:
        logger.error(f"Lỗi khi lưu lịch sử hội thoại: {e}")

def _add_to_conversation_history(user_message: str, ai_response: str):
    """Thêm tin nhắn vào lịch sử và giữ chỉ 20 tin nhắn gần nhất."""
    global _conversation_history
    
    # Thêm tin nhắn mới
    _conversation_history.append({
        "timestamp": datetime.now().isoformat(),
        "user": user_message,
        "ai": ai_response
    })
    
    # Giữ chỉ 20 tin nhắn gần nhất
    if len(_conversation_history) > 20:
        _conversation_history = _conversation_history[-20:]
    
    # Lưu vào file
    _save_conversation_history()

def _apply_memory_updates(new_memory: Dict[str, Any]) -> bool:
    """Thay thế toàn bộ memory bằng memory mới từ AI response."""
    global _user_memory
    
    try:
        if not new_memory:
            return False
        
        # Thay thế toàn bộ memory
        _user_memory = new_memory.copy()
        _user_memory['last_updated'] = datetime.now().isoformat()
        
        # Lưu vào file
        _save_user_memory()
        
        logger.info(f"Đã cập nhật toàn bộ memory: {len(_user_memory)} fields")
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật memory: {e}")
        return False

def _parse_ai_response(raw_response: str) -> Tuple[str, Dict[str, Any]]:
    """Parse AI response JSON và trích xuất main_response và new_memory."""
    try:
        logger.debug(f"Parsing raw response ({len(raw_response)} chars): {raw_response[:200]}...")
        
        # Loại bỏ markdown code blocks nếu có
        cleaned_response = raw_response.strip()
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]  # Bỏ ```json
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]  # Bỏ ```
        cleaned_response = cleaned_response.strip()
        
        # Thử parse toàn bộ response như JSON trước
        try:
            response_data = json.loads(cleaned_response)
            main_response = response_data.get('main_response', '')
            new_memory = response_data.get('new_memory', {})
            
            if main_response:
                logger.info(f"Successfully parsed full JSON - main_response: {len(main_response)} chars")
                return main_response, new_memory
        except json.JSONDecodeError:
            pass  # Tiếp tục với pattern matching
        
        # Tìm JSON trong response với pattern chính xác hơn
        json_patterns = [
            r'\{[^{}]*"main_response"[^{}]*"new_memory"[^{}]*\}',  # Pattern đầy đủ
            r'\{.*?"main_response".*?\}',  # Pattern linh hoạt
        ]
        
        for pattern in json_patterns:
            json_match = re.search(pattern, cleaned_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                logger.debug(f"Found JSON with pattern: {json_str[:100]}...")
                
                try:
                    response_data = json.loads(json_str)
                    main_response = response_data.get('main_response', '')
                    new_memory = response_data.get('new_memory', {})
                    
                    if main_response:
                        logger.info(f"Successfully parsed JSON - main_response: {len(main_response)} chars")
                        return main_response, new_memory
                except json.JSONDecodeError:
                    continue  # Thử pattern tiếp theo
        
        # Fallback: Tìm text sau "main_response": với escape characters
        fallback_patterns = [
            r'"main_response"\s*:\s*"([^"]*)"',
            r"'main_response'\s*:\s*'([^']*)'",
        ]
        
        for pattern in fallback_patterns:
            fallback_match = re.search(pattern, cleaned_response)
            if fallback_match:
                main_response = fallback_match.group(1)
                # Xử lý escape characters
                main_response = main_response.replace('\\"', '"').replace('\\n', '\n')
                logger.info(f"Fallback parse successful - main_response: {len(main_response)} chars")
                return main_response, {}
        
        # Cuối cùng: Cắt ngắn raw response để tránh TTS quá dài
        logger.warning("No JSON found, using truncated raw response")
        truncated_raw = _truncate_response(cleaned_response, 200)
        return truncated_raw, {}
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        # Fallback với truncated raw response
        truncated_raw = _truncate_response(raw_response, 200)
        return truncated_raw, {}
    except Exception as e:
        logger.error(f"Unexpected error parsing AI response: {e}")
        truncated_raw = _truncate_response(raw_response, 200)
        return truncated_raw, {}

def _truncate_response(text: str, max_length: int = None) -> str:
    """Cắt ngắn câu trả lời để tránh quá tải ESP32."""
    if max_length is None:
        max_length = int(os.getenv('GEMINI_MAX_RESPONSE_LENGTH', '200'))
    
    if len(text) <= max_length:
        return text
    
    # Cắt tại dấu câu gần nhất
    truncated = text[:max_length]
    
    # Tìm dấu câu cuối cùng
    for punct in ['.', '!', '?', ';']:
        last_punct = truncated.rfind(punct)
        if last_punct > max_length * 0.7:  # Chỉ cắt nếu không quá ngắn
            return truncated[:last_punct + 1]
    
    # Nếu không tìm thấy dấu câu, cắt tại từ
    words = truncated.split()
    if len(words) > 1:
        return ' '.join(words[:-1]) + '...'
    
    return truncated + '...'

def ask_gemini(question: str) -> Optional[str]:
    """
    Hỏi Gemini AI và nhận câu trả lời với các tính năng nâng cao.
    
    Args:
        question (str): Câu hỏi cần trả lời
        
    Returns:
        Optional[str]: Câu trả lời từ Gemini hoặc None nếu lỗi
    """
    if not question or not question.strip():
        logger.warning("Câu hỏi trống")
        return None
    
    # Tải bộ nhớ người dùng và lịch sử hội thoại
    _load_user_memory()
    _load_conversation_history()
    
    try:
        # Get client
        client = _get_client()
        
        # Get system prompt (ưu tiên custom prompt từ file)
        if _custom_system_prompt:
            system_prompt = _custom_system_prompt
        else:
            system_prompt = os.getenv('GEMINI_SYSTEM_PROMPT', 
                                     'Trả lời câu hỏi một cách ngắn gọn và chính xác bằng tiếng Việt. Giới hạn câu trả lời trong 100 ký tự.')
        
        # Thêm hướng dẫn JSON response mới
        json_instruction = '''

QUAN TRỌNG: Trả lời theo định dạng JSON sau:
{
  "main_response": "câu trả lời chính cho người dùng (tối đa 200 ký tự)",
  "new_memory": {
    "user_name": "tên người dùng",
    "preferences": "sở thích/thói quen",
    "personal_info": "thông tin cá nhân",
    "interests": "lĩnh vực quan tâm",
    "additional_info": "thông tin bổ sung khác"
  }
}

Hãy cập nhật và trả về TOÀN BỘ memory file mới dựa trên:
1. Memory hiện tại được cung cấp
2. Lịch sử 20 cuộc hội thoại gần nhất
3. Câu hỏi/thông tin mới từ người dùng

Nếu không có thông tin mới, hãy giữ nguyên memory cũ.
'''
        
        system_prompt += json_instruction
        
        # Thêm memory hiện tại
        if _user_memory:
            memory_context = "\n\nMEMORY HIỆN TẠI:\n"
            memory_context += json.dumps(_user_memory, ensure_ascii=False, indent=2)
            system_prompt += memory_context
        
        # Thêm lịch sử 20 cuộc hội thoại gần nhất
        if _conversation_history:
            history_context = "\n\nLỊCH SỬ 20 CUỘC HỘI THOẠI GẦN NHẤT:\n"
            for i, conv in enumerate(_conversation_history[-20:], 1):
                history_context += f"{i}. User: {conv['user']}\n   AI: {conv['ai']}\n"
            system_prompt += history_context
        
        # Create full prompt with system instruction
        full_prompt = f"{system_prompt}\n\nCÂU HỎI MỚI: {question}"
        
        logger.debug(f"Đang gửi câu hỏi tới Gemini: {question[:50]}...")
        
        # Call Gemini API
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt
        )
        
        raw_answer = response.text
        
        # Parse JSON response
        main_response, new_memory = _parse_ai_response(raw_answer)
        
        # Cập nhật memory nếu có memory mới
        if new_memory:
            _apply_memory_updates(new_memory)
        
        # Cắt ngắn câu trả lời để tránh quá tải ESP32
        truncated_answer = _truncate_response(main_response)
        
        # Thêm vào lịch sử hội thoại
        _add_to_conversation_history(question, truncated_answer)
        
        logger.info(f"Nhận được câu trả lời từ Gemini ({len(raw_answer)} ký tự, main_response: {len(truncated_answer)} ký tự)")
        logger.info(f"TTS sẽ sử dụng text: '{truncated_answer[:100]}...' ({len(truncated_answer)} ký tự)")
        if new_memory:
            logger.info(f"Cập nhật memory: {len(new_memory)} fields")
        
        return truncated_answer
        
    except Exception as e:
        logger.error(f"Lỗi khi gọi Gemini API: {e}")
        return None


def load_system_prompt_from_file(file_path: str) -> bool:
    """
    Tải system prompt từ file txt.
    
    Args:
        file_path (str): Đường dẫn tới file txt chứa system prompt
        
    Returns:
        bool: True nếu tải thành công, False nếu lỗi
    """
    global _custom_system_prompt
    
    try:
        # Tạo đường dẫn tuyệt đối
        if not os.path.isabs(file_path):
            file_path = Path(__file__).parent.parent / file_path
        else:
            file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File không tồn tại: {file_path}")
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            _custom_system_prompt = f.read().strip()
        
        logger.info(f"Đã tải system prompt từ file: {file_path} ({len(_custom_system_prompt)} ký tự)")
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi tải system prompt từ file {file_path}: {e}")
        return False

def reset_system_prompt():
    """Reset system prompt về mặc định."""
    global _custom_system_prompt
    _custom_system_prompt = None
    logger.info("Đã reset system prompt về mặc định")

def get_user_memory() -> Dict[str, Any]:
    """Lấy thông tin bộ nhớ người dùng."""
    _load_user_memory()
    return _user_memory.copy()

def clear_user_memory():
    """Xóa bộ nhớ người dùng."""
    global _user_memory
    _user_memory = {}
    _save_user_memory()
    logger.info("Đã xóa bộ nhớ người dùng")

# Alias cho dễ sử dụng
gemini_ask = ask_gemini


