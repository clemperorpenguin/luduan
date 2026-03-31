-- Korean (한국어) UI Strings for Luduan Plugin
return {
    -- Plugin name
    plugin_name = "루두안 오디오북",
    
    -- Menu items
    menu_enable = "루두안 활성화",
    menu_disable = "루두안 비활성화",
    menu_settings = "루두안 설정...",
    menu_play = "오디오 재생",
    menu_pause = "일시정지",
    menu_stop = "중지",
    menu_next = "다음 단락",
    menu_prev = "이전 단락",
    
    -- Status messages
    status_playing = "재생 중...",
    status_paused = "일시정지됨",
    status_stopped = "중지됨",
    status_loading = "로딩 중...",
    status_no_audio = "이 책의 오디오를 사용할 수 없습니다",
    status_no_translation = "번역을 사용할 수 없습니다",
    status_tts_mode = "TTS 모드",
    status_bluetooth_connected = "블루투스 연결됨",
    status_bluetooth_disconnected = "블루투스 연결 끊김",
    
    -- Translation display
    translation_label = "번역:",
    original_label = "원문:",
    
    -- Controls
    control_play = "재생",
    control_pause = "일시정지",
    control_stop = "중지",
    control_rewind = "10 초 되감기",
    control_forward = "10 초 앞으로",
    control_speed = "속도",
    control_close = "닫기",
    control_settings = "설정",
    
    -- Settings dialog
    settings_title = "루두안 설정",
    settings_playback = "재생",
    settings_display = "표시",
    settings_highlight = "강조",
    settings_language = "언어",
    settings_advanced = "고급",
    
    -- Playback settings
    setting_auto_play = "탭 시 자동 재생",
    setting_auto_play_desc = "단락을 탭할 때 자동으로 재생 시작",
    setting_playback_speed = "재생 속도",
    setting_volume_boost = "볼륨 부스트",
    setting_bluetooth_only = "블루투스 전용",
    setting_bluetooth_only_desc = "블루투스 연결 시에만 오디오 재생",
    
    -- Display settings
    setting_show_translation = "번역 표시",
    setting_translation_position = "번역 위치",
    setting_position_overlay = "오버레이",
    setting_position_bottom = "하단 패널",
    setting_position_top = "상단 패널",
    setting_font_size = "글꼴 크기",
    setting_font_family = "글꼴",
    setting_opacity = "불투명도",
    
    -- Highlight settings
    setting_enable_highlight = "강조 활성화",
    setting_highlight_color = "강조 색상",
    setting_highlight_opacity = "강조 불투명도",
    setting_animate_highlight = "강조 애니메이션",
    
    -- Language settings
    setting_ui_language = "인터페이스 언어",
    setting_preferred_translation = "선호 번역",
    setting_tts_fallback = "TTS 폴백",
    setting_tts_fallback_desc = "번역이 없을 때 텍스트 음성 변환 사용",
    
    -- Advanced settings
    setting_tap_to_pause = "탭하여 일시정지/재개",
    setting_auto_scroll = "자동 스크롤",
    setting_auto_scroll_desc = "현재 단락을 화면에 유지",
    setting_close_on_complete = "완료 시 닫기",
    setting_show_progress = "진행률 표시줄 표시",
    setting_debug_mode = "디버그 모드",
    
    -- Colors
    color_yellow = "노란색",
    color_green = "초록색",
    color_blue = "파란색",
    color_purple = "보라색",
    color_orange = "주황색",
    color_red = "빨간색",
    
    -- Speed options
    speed_0_5x = "0.5×",
    speed_0_75x = "0.75×",
    speed_1_0x = "1.0×",
    speed_1_25x = "1.25×",
    speed_1_5x = "1.5×",
    speed_2_0x = "2.0×",
    
    -- Errors
    error_title = "오류",
    error_audio_load = "오디오 파일을 로드할 수 없음",
    error_manifest_load = "매니페스트를 로드할 수 없음",
    error_playback = "재생 오류",
    error_file_not_found = "파일을 찾을 수 없음",
    error_bluetooth = "블루투스 오류",
    
    -- Confirmations
    confirm_reset = "모든 설정을 기본값으로 재설정하시겠습니까?",
    confirm_close = "플레이어를 닫으시겠습니까?",
    
    -- Time format
    time_format = "%02d:%02d",
    time_remaining = "남음：%s",
    time_elapsed = "경과：%s",
}
