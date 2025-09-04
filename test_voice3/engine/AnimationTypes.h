#pragma once
#include "../generated/vector_shapes.h" // Dùng ../ để đi ngược ra thư mục gốc
#include "../directors/EmotionManager.h" // Include để sử dụng Emotion struct

enum EmotionState {
    NEUTRAL,
    HAPPY,
    ANGRY,
    SAD,
    BLINK, // Thêm trạng thái Blink
    NO_CHANGE
};

enum EasingType {
    LINEAR,
    EASE_IN_OUT_QUAD
};

struct AnimationState {
    bool is_playing = false;
    bool is_paused = false;
    
    unsigned long start_time = 0;
    float duration_sec = 0.0;
    
    // Sử dụng con trỏ đến struct Emotion thay vì enum EmotionState
    const Emotion* start_state = nullptr;
    const Emotion* end_state = nullptr;
    
    float intensity = 1.0;
    EasingType easing = LINEAR;
    
    float paused_progress = 0.0;
    
    // Thời gian tồn tại của cảm xúc (dwell time)
    unsigned long dwell_time = 0;
};