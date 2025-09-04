// FILE NÀY ĐƯỢC TẠO TỰ ĐỘNG. KHÔNG CHỈNH SỬA BẰNG TAY.
#pragma once
#include "../generated/vector_shapes.h"

struct Emotion {
    const char* name;
    const Point* left_shape;
    const Point* right_shape;
};

const int EMOTION_COUNT = 9;
const Emotion emotions[EMOTION_COUNT] = {
    {"angry", angry_left_shape, angry_right_shape},
    {"blink", blink_left_shape, blink_right_shape},
    {"happy", happy_left_shape, happy_right_shape},
    {"love", love_left_shape, love_right_shape},
    {"neutral", neutral_left_shape, neutral_right_shape},
    {"sad", sad_left_shape, sad_right_shape},
    {"surprise", surprise_left_shape, surprise_right_shape},
    {"sus", sus_left_shape, sus_right_shape},
    {"sus2", sus2_left_shape, sus2_right_shape}
};

const int NEUTRAL_STATE_INDEX = 4;