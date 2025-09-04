#include "engine/AnimationEngine.h"
#include "config.h"
#include <U8g2lib.h>
#include <string.h>

// Khai báo biến u8g2 từ file .ino chính
extern U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2;

// --- BIẾN TRẠNG THÁI CỦA ENGINE ---
AnimationState emotion_anim;
AnimationState blink_anim;

// Mảng RAM tạm thời để chứa tọa độ của frame sẽ được vẽ
Point current_left_eye[EYE_VERTEX_COUNT];
Point current_right_eye[EYE_VERTEX_COUNT];

// Biến trạng thái cho hướng nhìn (Gaze)
float gaze_offset_x = 0.0;
float gaze_offset_y = 0.0;

// MỚI: Các biến để quản lý animation của Gaze
bool is_gaze_transitioning = false;
unsigned long gaze_start_time = 0;
float gaze_duration_sec = 0.0;
float gaze_start_offset_x = 0.0;
float gaze_target_offset_x = 0.0;

// --- CÁC HÀM TIỆN ÍCH ---

// Nội suy tuyến tính
float linear_interpolate(float start, float end, float t) {
    return start + t * (end - start);
}

// Áp dụng quy luật chuyển động (easing)
float apply_easing(float t, EasingType easing) {
    if (easing == EASE_IN_OUT_QUAD) {
        if (t < 0.5) return 2 * t * t;
        return -1 + (4 - 2 * t) * t;
    }
    return t; // Mặc định là LINEAR
}

// Hàm nội bộ để tính toán và điền vào mảng current_..._eye
void calculate_current_frame(const AnimationState* anim, float progress) {
    const Point* start_l = anim->start_state->left_shape;
    const Point* start_r = anim->start_state->right_shape;
    const Point* end_l = anim->end_state->left_shape;
    const Point* end_r = anim->end_state->right_shape;

    for (int i = 0; i < EYE_VERTEX_COUNT; i++) {
        current_left_eye[i].x = (int16_t)linear_interpolate(start_l[i].x, end_l[i].x, progress);
        current_left_eye[i].y = (int16_t)linear_interpolate(start_l[i].y, end_l[i].y, progress);
        current_right_eye[i].x = (int16_t)linear_interpolate(start_r[i].x, end_r[i].x, progress);
        current_right_eye[i].y = (int16_t)linear_interpolate(start_r[i].y, end_r[i].y, progress);
    }
}

// --- CÁC HÀM CHÍNH CỦA ENGINE ---

void animation_engine_initialize() {
    // Lấy trạng thái neutral từ mảng emotions do Python tạo ra
    const Emotion* neutral_state = &emotions[NEUTRAL_STATE_INDEX];
    // Sao chép hình dạng ban đầu vào mảng vẽ
    memcpy(current_left_eye, neutral_state->left_shape, EYE_VERTEX_COUNT * sizeof(Point));
    memcpy(current_right_eye, neutral_state->right_shape, EYE_VERTEX_COUNT * sizeof(Point));
    
    // Thiết lập trạng thái cuối cùng của emotion_anim để các lệnh sau biết bắt đầu từ đâu
    emotion_anim.end_state = neutral_state;
}

bool animation_engine_is_busy() {
    return emotion_anim.is_playing || blink_anim.is_playing;
}

void animation_engine_change_emotion(const Emotion* start, const Emotion* target, float duration, float intensity, EasingType easing, unsigned long dwell_time) {
    if (emotion_anim.is_playing) return; // Chỉ nhận lệnh mới khi rảnh

    emotion_anim.is_playing = true;
    emotion_anim.is_paused = false;
    emotion_anim.start_time = millis();
    emotion_anim.duration_sec = duration;
    emotion_anim.start_state = start;
    emotion_anim.end_state = target;
    emotion_anim.intensity = intensity;
    emotion_anim.easing = easing;
    
    // Lưu thời gian dwell để Emotion Director có thể sử dụng
    emotion_anim.dwell_time = dwell_time;
}

void animation_engine_start_blink() {
    if (blink_anim.is_playing) return; // Tránh chớp mắt chồng chéo

    // Tìm trạng thái BLINK trong mảng emotions
    const Emotion* blink_state = nullptr;
    for(int i = 0; i < EMOTION_COUNT; i++) {
        if (strcmp(emotions[i].name, "blink") == 0) {
            blink_state = &emotions[i];
            break;
        }
    }
    if (blink_state == nullptr) return; // Không tìm thấy hình dạng blink, không làm gì cả

    // Tạm dừng animation cảm xúc hiện tại
    if (emotion_anim.is_playing) {
        emotion_anim.is_paused = true;
        unsigned long elapsed = millis() - emotion_anim.start_time;
        emotion_anim.paused_progress = (float)elapsed / (emotion_anim.duration_sec * 1000.0f);
    }

    // Bắt đầu animation chớp mắt
    blink_anim.is_playing = true;
    blink_anim.is_paused = false;
    blink_anim.start_time = millis();
    blink_anim.duration_sec = 0.25f; // Chớp mắt nhanh trong 0.25 giây
    blink_anim.start_state = emotion_anim.end_state; // Bắt đầu từ trạng thái mắt hiện tại
    blink_anim.end_state = blink_state;
    blink_anim.easing = EASE_IN_OUT_QUAD;
    blink_anim.intensity = 1.0;
}

// NÂNG CẤP: Hàm Gaze mới, mạnh mẽ hơn
void animation_engine_start_gaze_transition(float target_offset_x, float duration) {
    if (is_gaze_transitioning) return; // Bỏ qua nếu đang liếc dở

    is_gaze_transitioning = true;
    gaze_start_time = millis();
    gaze_duration_sec = duration;
    gaze_start_offset_x = gaze_offset_x; // Bắt đầu từ vị trí hiện tại
    gaze_target_offset_x = target_offset_x;
}


void animation_engine_update() {
    // =========================================================================
    // GIAI ĐOẠN 1: CẬP NHẬT CÁC TRẠNG THÁI LOGIC (KHÔNG VẼ)
    // =========================================================================

    // --- CẬP NHẬT LOGIC HƯỚNG NHÌN (GAZE) ---
    if (is_gaze_transitioning) {
        unsigned long elapsed = millis() - gaze_start_time;
        float progress = (float)elapsed / (gaze_duration_sec * 1000.0f);

        if (progress >= 1.0f) {
            progress = 1.0f;
            is_gaze_transitioning = false; // Kết thúc animation liếc mắt
        }
        
        // Cập nhật giá trị gaze_offset_x một cách mượt mà
        gaze_offset_x = linear_interpolate(gaze_start_offset_x, gaze_target_offset_x, apply_easing(progress, EASE_IN_OUT_QUAD));
    }

    // --- CẬP NHẬT LOGIC HÌNH DẠNG MẮT (SHAPE) ---
    // Ưu tiên xử lý chớp mắt trước
    if (blink_anim.is_playing) {
        unsigned long elapsed = millis() - blink_anim.start_time;
        float raw_progress = (float)elapsed / (blink_anim.duration_sec * 1000.0f);

        // Logic chớp mắt: nửa đầu đi xuống (nhắm mắt), nửa sau đi lên (mở mắt)
        if (raw_progress < 0.5f) {
            // Đi từ trạng thái hiện tại -> BLINK
            float progress = raw_progress * 2.0f; // Chuyển progress từ 0->0.5 thành 0->1.0
            float eased_progress = apply_easing(progress, blink_anim.easing);
            calculate_current_frame(&blink_anim, eased_progress);
        } else {
            // Đi từ BLINK -> trạng thái hiện tại
            float progress = (raw_progress - 0.5f) * 2.0f; // Chuyển progress từ 0.5->1.0 thành 0->1.0
            float eased_progress = apply_easing(progress, blink_anim.easing);
            
            // Đảo ngược start và end để mở mắt
            AnimationState temp_anim = blink_anim; // Tạo bản sao để không thay đổi anim gốc
            temp_anim.start_state = blink_anim.end_state;   // Bắt đầu từ BLINK
            temp_anim.end_state = blink_anim.start_state;     // Kết thúc ở trạng thái cũ
            calculate_current_frame(&temp_anim, eased_progress);
        }

        // Kiểm tra kết thúc animation chớp mắt
        if (raw_progress >= 1.0f) {
            blink_anim.is_playing = false;
            // Tiếp tục animation cảm xúc nếu nó đã bị tạm dừng
            if (emotion_anim.is_paused) {
                emotion_anim.is_paused = false;
                // Tính lại start_time để tiếp tục từ điểm đã dừng
                unsigned long new_offset = (unsigned long)(emotion_anim.duration_sec * 1000.0f * emotion_anim.paused_progress);
                emotion_anim.start_time = millis() - new_offset;
            }
        }
    } 
    // Nếu không chớp mắt, xử lý animation cảm xúc
    else if (emotion_anim.is_playing && !emotion_anim.is_paused) {
        unsigned long elapsed = millis() - emotion_anim.start_time;
        float raw_progress = (float)elapsed / (emotion_anim.duration_sec * 1000.0f);

        if (raw_progress >= 1.0f) {
            raw_progress = 1.0f;
            emotion_anim.is_playing = false; // Đánh dấu animation kết thúc
        }
        
        float eased_progress = apply_easing(raw_progress, emotion_anim.easing);
        float final_progress = eased_progress * emotion_anim.intensity;
        calculate_current_frame(&emotion_anim, final_progress);
    }
    // Nếu không có animation nào đang chạy, `current_..._eye` sẽ giữ nguyên giá trị từ lần tính toán cuối cùng.

    // =========================================================================
    // GIAI ĐOẠN 2: ÁP DỤNG BIẾN ĐỔI (TRANSFORM) VÀ VẼ
    // =========================================================================
    
    // (Toàn bộ logic tính toán final_left_eye, final_right_eye và vẽ bằng drawTriangle không đổi)
    // Nó sẽ tự động sử dụng giá trị gaze_offset_x đã được cập nhật mượt mà ở trên.
    
    // Mảng RAM tạm thời để chứa tọa độ cuối cùng sau khi biến đổi
    Point final_left_eye[EYE_VERTEX_COUNT];
    Point final_right_eye[EYE_VERTEX_COUNT];

    // Các tham số cho hiệu ứng phối cảnh
    const float PERSPECTIVE_SCALE_AMOUNT = 0.15f; // Mắt xa sẽ nhỏ hơn 15%
    const float MAX_GAZE_OFFSET = 10.0f; // Phải khớp với giá trị trong hàm look_left/right

    // Tính toán hệ số co giãn cho mỗi mắt dựa trên hướng nhìn
    float scale_left = 1.0f - (gaze_offset_x / MAX_GAZE_OFFSET) * PERSPECTIVE_SCALE_AMOUNT;
    float scale_right = 1.0f + (gaze_offset_x / MAX_GAZE_OFFSET) * PERSPECTIVE_SCALE_AMOUNT;

    // Tính toán tâm của mỗi mắt để co giãn cho đúng
    long left_center_x = 0, left_center_y = 0;
    long right_center_x = 0, right_center_y = 0;
    for(int i=0; i<EYE_VERTEX_COUNT; ++i) {
        left_center_x += current_left_eye[i].x;
        left_center_y += current_left_eye[i].y;
        right_center_x += current_right_eye[i].x;
        right_center_y += current_right_eye[i].y;
    }
    left_center_x /= EYE_VERTEX_COUNT;
    left_center_y /= EYE_VERTEX_COUNT;
    right_center_x /= EYE_VERTEX_COUNT;
    right_center_y /= EYE_VERTEX_COUNT;

    // Áp dụng các phép biến đổi (dịch chuyển + co giãn) cho từng điểm
    for (int i = 0; i < EYE_VERTEX_COUNT; i++) {
        // Mắt trái
        float temp_lx = current_left_eye[i].x - left_center_x;
        float temp_ly = current_left_eye[i].y - left_center_y;
        final_left_eye[i].x = (int16_t)(temp_lx * scale_left + left_center_x + gaze_offset_x);
        final_left_eye[i].y = (int16_t)(temp_ly * scale_left + left_center_y + gaze_offset_y);

        // Mắt phải
        float temp_rx = current_right_eye[i].x - right_center_x;
        float temp_ry = current_right_eye[i].y - right_center_y;
        final_right_eye[i].x = (int16_t)(temp_rx * scale_right + right_center_x + gaze_offset_x);
        final_right_eye[i].y = (int16_t)(temp_ry * scale_right + right_center_y + gaze_offset_y);
    }

    // Luôn vẽ frame hiện tại lên màn hình bằng dữ liệu đã biến đổi
    u8g2.clearBuffer();
    for (int i = 1; i < EYE_VERTEX_COUNT - 1; i++) {
        u8g2.drawTriangle(final_left_eye[0].x, final_left_eye[0].y, final_left_eye[i].x, final_left_eye[i].y, final_left_eye[i+1].x, final_left_eye[i+1].y);
        u8g2.drawTriangle(final_right_eye[0].x, final_right_eye[0].y, final_right_eye[i].x, final_right_eye[i].y, final_right_eye[i+1].x, final_right_eye[i+1].y);
    }
    u8g2.sendBuffer();
}