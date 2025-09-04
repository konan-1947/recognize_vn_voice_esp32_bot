#pragma once
#include "../directors/EmotionManager.h" // File do Python tạo, chứa danh sách Emotion
#include "AnimationTypes.h" // Include để sử dụng EasingType và AnimationState

// Function declarations
void animation_engine_initialize();
bool animation_engine_is_busy();
void animation_engine_change_emotion(const Emotion* start, const Emotion* target, float duration, float intensity, EasingType easing, unsigned long dwell_time);
void animation_engine_start_blink();
void animation_engine_update();

// NÂNG CẤP: Các hàm Gaze bây giờ nhận vào thời gian chuyển đổi
void animation_engine_start_gaze_transition(float target_offset_x, float duration);

// MỚI: Cho phép các file khác thấy được trạng thái của Gaze animation
extern bool is_gaze_transitioning;