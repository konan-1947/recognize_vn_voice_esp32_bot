# Audio Utils Package
# Chứa các hàm xử lý audio chung cho server

from .audio_processing import audio_preprocessing_improved
from .speech_recognition import transcribe_audio_with_google
from .file_utils import save_audio_to_wav, save_transcription_to_txt
from .dependencies import check_audio_dependencies, get_installation_commands
from .transcript_logger import TranscriptLogger
from .server_config import *
from .udp_handler import send_led_command, udp_listener
from .wake_word_handler import check_wake_word, process_wake_word_detection, process_question_capture, reset_question_mode
from .asr_processor import asr_worker
from .flask_server import create_app, create_templates
from .gemini_api import ask_gemini, gemini_ask
from .tts_utils import text_to_audio_file, play_audio_file, text_to_speech

__all__ = [
    'audio_preprocessing_improved',
    'transcribe_audio_with_google', 
    'save_audio_to_wav',
    'save_transcription_to_txt',
    'check_audio_dependencies',
    'get_installation_commands',
    'TranscriptLogger',
    # Server configuration
    'HOST', 'UDP_PORT', 'FLASK_PORT', 'COMMAND_PORT', 'WAKE_WORD',
    'q_audio', 'esp32_address', 'is_listening_for_question', 'shutdown_event',
    'transcript_logger', 'question_logger',
    # UDP handler
    'send_led_command', 'udp_listener',
    # Wake word handler
    'check_wake_word', 'process_wake_word_detection', 'process_question_capture', 'reset_question_mode',
    # ASR processor
    'asr_worker',
    # Flask server
    'create_app', 'create_templates',
    # Gemini AI integration
    'ask_gemini', 'gemini_ask',
    # TTS utils
    'text_to_audio_file', 'play_audio_file', 'text_to_speech'
] 