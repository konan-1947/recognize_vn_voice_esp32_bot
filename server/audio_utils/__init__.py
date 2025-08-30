# Audio Utils Package
# Chứa các hàm xử lý audio chung cho server

from .audio_processing import audio_preprocessing_improved
from .speech_recognition import transcribe_audio_with_google
from .file_utils import save_audio_to_wav, save_transcription_to_txt
from .dependencies import check_audio_dependencies, get_installation_commands
from .transcript_logger import TranscriptLogger

__all__ = [
    'audio_preprocessing_improved',
    'transcribe_audio_with_google', 
    'save_audio_to_wav',
    'save_transcription_to_txt',
    'check_audio_dependencies',
    'get_installation_commands',
    'TranscriptLogger'
] 