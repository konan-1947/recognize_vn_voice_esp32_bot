#pragma once

// MỚI: Enum để quản lý trạng thái của Gaze Director
enum GazeState {
    GAZE_IDLE,
    GAZE_TRANSITION_TO_SIDE,
    GAZE_DWELLING_AT_SIDE,
    GAZE_TRANSITION_TO_CENTER
};

void initialize_directors();
bool blink_director_update();
void emotion_director_update();
void gaze_director_update();