#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Server Module - Flask + SocketIO application và routes
"""

import time
import os
from flask import Flask, render_template
from flask_socketio import SocketIO

from .server_config import (
    UDP_PORT, FLASK_PORT, COMMAND_PORT, GOOGLE_SPEECH_LANGUAGE,
    WAKE_WORD, q_audio, esp32_address
)

def create_app():
    """Tạo Flask application"""
    app = Flask(__name__)
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    @app.route('/')
    def index():
        """Trang chủ với giao diện real-time transcript"""
        return render_template("index.html")

    @app.route('/status')
    def status():
        """API trạng thái server"""
        return {
            "status": "running",
            "speech_engine": "Google Speech Recognition + Circular Buffer",
            "language": GOOGLE_SPEECH_LANGUAGE,
            "udp_port": UDP_PORT,
            "command_port": COMMAND_PORT,
            "flask_port": FLASK_PORT,
            "audio_queue_size": len(q_audio),
            "wake_word": WAKE_WORD,
            "esp32_connected": esp32_address is not None,
            "esp32_address": esp32_address[0] if esp32_address else None
        }

    @app.route('/test')
    def test():
        """Test kết nối"""
        return {"message": "Server hoạt động bình thường", "timestamp": time.time()}

    @app.route('/transcript-stats')
    def transcript_stats():
        """API thống kê transcript log"""
        try:
            import audio_utils.server_config as config
            if config.transcript_logger:
                stats = config.transcript_logger.get_stats()
                return {
                    "transcript_log": {
                        "filepath": config.transcript_logger.get_filepath(),
                        "stats": stats
                    }
                }
            else:
                return {"error": "Transcript logger chưa được khởi tạo"}
        except Exception as e:
            return {"error": str(e)}
    
    return app, socketio

def create_templates():
    """Tạo thư mục templates nếu chưa có - HTML template đã được tách riêng"""
    os.makedirs("templates", exist_ok=True)
    print("✅ Templates directory đã sẵn sàng")