#include "directors/Directors.h"
#include "directors/EmotionManager.h" // File do Python tạo, chứa danh sách Emotion
#include "./engine/AnimationEngine.h"
#include "./config.h"
#include <Arduino.h>

// =========================================================================
// BIẾN TRẠNG THÁI NỘI BỘ CỦA CÁC "BỘ NÃO"
// =========================================================================

// --- Biến cho "Bộ não Chớp mắt" (Blink Director) ---
unsigned long last_blink_time = 0;
unsigned long next_blink_interval = 0;

// --- Biến cho "Bộ não Cảm xúc" (Emotion Director) ---
const Emotion* current_emotion = &emotions[NEUTRAL_STATE_INDEX]; // "Trí nhớ" về cảm xúc hiện tại
unsigned long emotion_state_start_time = 0;     // Thời điểm bắt đầu trạng thái hiện tại
unsigned long current_emotion_dwell_time = 0;   // Thời gian cần ở lại trong trạng thái này

// --- BIẾN TRẠNG THÁI CHO GAZE DIRECTOR (NÂNG CẤP) ---
GazeState current_gaze_state = GAZE_IDLE;
unsigned long gaze_state_start_time = 0;
unsigned long next_gaze_action_interval = 0; // Thời gian chờ ở trạng thái IDLE
float gaze_target_offset = 0.0f;


// =========================================================================
// CÁC HÀM CỦA "BỘ NÃO"
// =========================================================================

void initialize_directors() {
    // Khởi tạo Blink Director
    last_blink_time = millis();
    next_blink_interval = random(BLINK_INTERVAL_MIN, BLINK_INTERVAL_MAX);

    // Khởi tạo Emotion Director
    emotion_state_start_time = millis();
    current_emotion_dwell_time = random(NEUTRAL_DWELL_MIN, NEUTRAL_DWELL_MAX);

    // Khởi tạo Gaze Director
    gaze_state_start_time = millis();
    next_gaze_action_interval = random(4000, 8000); // Lần liếc mắt đầu tiên
}

// --- BỘ NÃO CHỚP MẮT ---
// Quyết định KHI NÀO cần chớp mắt.
bool blink_director_update() {
    if (millis() - last_blink_time > next_blink_interval) {
        last_blink_time = millis();
        next_blink_interval = random(BLINK_INTERVAL_MIN, BLINK_INTERVAL_MAX);
        return true; // Trả về TRUE để báo cho main loop biết cần hành động
    }
    return false;
}

// --- BỘ NÃO CẢM XÚC ---
// Quyết định CẢM XÚC tiếp theo là gì.
void emotion_director_update() {
    // Điều kiện tiên quyết: Engine phải rảnh và đã hết thời gian tồn tại của cảm xúc cũ
    if (animation_engine_is_busy() || (millis() - emotion_state_start_time < current_emotion_dwell_time)) {
        return; // Chưa đến lúc, không làm gì cả
    }

    // Đã đến lúc ra quyết định mới
    const Emotion* next_emotion = nullptr;
    const Emotion* start_emotion = current_emotion;

    // Logic quyết định dựa trên trạng thái hiện tại
    if (strcmp(current_emotion->name, "neutral") != 0) {
        // Nếu đang có cảm xúc, 80% cơ hội quay về NEUTRAL
        if (random(10) < 8) {
            next_emotion = &emotions[NEUTRAL_STATE_INDEX];
        }
        // 20% còn lại là không làm gì, tiếp tục giữ cảm xúc cũ (bằng cách để next_emotion là nullptr)
    } else {
        // Nếu đang NEUTRAL, 60% cơ hội chuyển sang cảm xúc mới
        if (random(10) < 6) {
            int next_index;
            do {
                next_index = random(EMOTION_COUNT);
            } while (next_index == NEUTRAL_STATE_INDEX); // Đảm bảo không chọn lại neutral
            next_emotion = &emotions[next_index];
        }
        // 40% còn lại là không làm gì, tiếp tục ở trạng thái NEUTRAL
    }

    // Nếu đã có quyết định thay đổi, hãy ra lệnh cho engine
    if (next_emotion != nullptr) {
        // Tạo các tham số ngẫu nhiên cho animation
        float duration = random(30, 71) / 100.0f; // Thời gian chuyển đổi từ 0.3 đến 0.7 giây
        
        // Tính thời gian tồn tại cho cảm xúc mới
        unsigned long dwell_time;
        if (strcmp(next_emotion->name, "neutral") == 0) {
            dwell_time = random(NEUTRAL_DWELL_MIN, NEUTRAL_DWELL_MAX);
        } else {
            dwell_time = random(EMOTION_DWELL_MIN, EMOTION_DWELL_MAX);
        }
        
        // Ra lệnh
        animation_engine_change_emotion(start_emotion, next_emotion, duration, 1.0f, EASE_IN_OUT_QUAD, dwell_time);
        
        // Cập nhật "trí nhớ" của bộ não
        current_emotion = next_emotion;
        current_emotion_dwell_time = dwell_time;
    }
    
    // Reset bộ đếm thời gian cho trạng thái hiện tại
    emotion_state_start_time = millis();
}

// --- BỘ NÃO HƯỚNG NHÌN (VIẾT LẠI HOÀN TOÀN) ---
void gaze_director_update() {
    // "Bộ não" này không hành động nếu có animation cảm xúc hoặc chớp mắt đang chạy
    if (animation_engine_is_busy()) {
        return;
    }

    unsigned long current_time = millis();

    switch (current_gaze_state) {
        case GAZE_IDLE: {
            // Trạng thái nghỉ, mắt nhìn thẳng. Chờ đến lúc hành động.
            if (current_time - gaze_state_start_time > next_gaze_action_interval) {
                // Đã đến lúc liếc mắt
                int choice = random(10);
                if (choice < 7) { // 70% cơ hội liếc mắt
                    gaze_target_offset = (random(2) == 0) ? -10.0f : 10.0f; // Ngẫu nhiên trái hoặc phải
                    float gaze_duration = 0.25f; // Liếc sang bên trong 0.25 giây

                    animation_engine_start_gaze_transition(gaze_target_offset, gaze_duration);
                    
                    // Chuyển sang trạng thái tiếp theo
                    current_gaze_state = GAZE_TRANSITION_TO_SIDE;
                    gaze_state_start_time = current_time;
                } else {
                    // 30% còn lại là không làm gì, chỉ reset bộ đếm
                    gaze_state_start_time = current_time;
                    next_gaze_action_interval = random(4000, 8000);
                }
            }
            break;
        }

        case GAZE_TRANSITION_TO_SIDE: {
            // Đang trong quá trình liếc sang bên. Chờ cho engine hoàn thành.
            // is_gaze_transitioning là biến trong AnimationEngine
            if (!is_gaze_transitioning) { 
                // Engine đã liếc xong, chuyển sang trạng thái dừng lại
                current_gaze_state = GAZE_DWELLING_AT_SIDE;
                gaze_state_start_time = current_time;
            }
            break;
        }

        case GAZE_DWELLING_AT_SIDE: {
            // Đã liếc xong, đang dừng lại ở bên đó.
            // Thời gian dừng lại ngẫu nhiên, không quá nửa giây (ví dụ: 100-400ms)
            const unsigned long dwell_duration = random(100, 401); 
            if (current_time - gaze_state_start_time > dwell_duration) {
                // Đã dừng đủ lâu, ra lệnh quay về trung tâm
                float return_duration = 0.3f; // Quay về trong 0.3 giây
                animation_engine_start_gaze_transition(0.0f, return_duration); // 0.0f là vị trí trung tâm

                // Chuyển sang trạng thái tiếp theo
                current_gaze_state = GAZE_TRANSITION_TO_CENTER;
                gaze_state_start_time = current_time;
            }
            break;
        }

        case GAZE_TRANSITION_TO_CENTER: {
            // Đang trong quá trình liếc về trung tâm. Chờ cho engine hoàn thành.
            if (!is_gaze_transitioning) {
                // Đã về đến trung tâm, quay lại trạng thái nghỉ
                current_gaze_state = GAZE_IDLE;
                gaze_state_start_time = current_time;
                // Lên lịch cho lần liếc mắt tiếp theo
                next_gaze_action_interval = random(4000, 8000);
            }
            break;
        }
    }
}