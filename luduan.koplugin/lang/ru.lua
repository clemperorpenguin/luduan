-- Russian (Русский) UI Strings for Luduan Plugin
return {
    -- Plugin name
    plugin_name = "Аудиокнига Luduan",
    
    -- Menu items
    menu_enable = "Включить Luduan",
    menu_disable = "Отключить Luduan",
    menu_settings = "Настройки Luduan...",
    menu_play = "Воспроизвести аудио",
    menu_pause = "Пауза",
    menu_stop = "Стоп",
    menu_next = "Следующий абзац",
    menu_prev = "Предыдущий абзац",
    
    -- Status messages
    status_playing = "Воспроизведение...",
    status_paused = "На паузе",
    status_stopped = "Остановлено",
    status_loading = "Загрузка...",
    status_no_audio = "Нет аудио для этой книги",
    status_no_translation = "Нет перевода",
    status_tts_mode = "Режим TTS",
    status_bluetooth_connected = "Bluetooth подключен",
    status_bluetooth_disconnected = "Bluetooth отключен",
    
    -- Translation display
    translation_label = "Перевод:",
    original_label = "Оригинал:",
    
    -- Controls
    control_play = "Воспроизвести",
    control_pause = "Пауза",
    control_stop = "Стоп",
    control_rewind = "Назад 10 сек",
    control_forward = "Вперед 10 сек",
    control_speed = "Скорость",
    control_close = "Закрыть",
    control_settings = "Настройки",
    
    -- Settings dialog
    settings_title = "Настройки Luduan",
    settings_playback = "Воспроизведение",
    settings_display = "Отображение",
    settings_highlight = "Подсветка",
    settings_language = "Язык",
    settings_advanced = "Дополнительно",
    
    -- Playback settings
    setting_auto_play = "Автовоспроизведение при касании",
    setting_auto_play_desc = "Автоматически начинать воспроизведение при касании абзаца",
    setting_playback_speed = "Скорость воспроизведения",
    setting_volume_boost = "Усиление громкости",
    setting_bluetooth_only = "Только Bluetooth",
    setting_bluetooth_only_desc = "Воспроизводить аудио только при подключенном Bluetooth",
    
    -- Display settings
    setting_show_translation = "Показывать перевод",
    setting_translation_position = "Положение перевода",
    setting_position_overlay = "Наложение",
    setting_position_bottom = "Нижняя панель",
    setting_position_top = "Верхняя панель",
    setting_font_size = "Размер шрифта",
    setting_font_family = "Шрифт",
    setting_opacity = "Непрозрачность",
    
    -- Highlight settings
    setting_enable_highlight = "Включить подсветку",
    setting_highlight_color = "Цвет подсветки",
    setting_highlight_opacity = "Непрозрачность подсветки",
    setting_animate_highlight = "Анимация подсветки",
    
    -- Language settings
    setting_ui_language = "Язык интерфейса",
    setting_preferred_translation = "Предпочитаемый перевод",
    setting_tts_fallback = "Резервный TTS",
    setting_tts_fallback_desc = "Использовать синтез речи при отсутствии перевода",
    
    -- Advanced settings
    setting_tap_to_pause = "Касание для паузы/возобновления",
    setting_auto_scroll = "Автопрокрутка",
    setting_auto_scroll_desc = "Держать текущий абзац в поле зрения",
    setting_close_on_complete = "Закрыть по завершении",
    setting_show_progress = "Показывать прогресс-бар",
    setting_debug_mode = "Режим отладки",
    
    -- Colors
    color_yellow = "Желтый",
    color_green = "Зеленый",
    color_blue = "Синий",
    color_purple = "Фиолетовый",
    color_orange = "Оранжевый",
    color_red = "Красный",
    
    -- Speed options
    speed_0_5x = "0.5×",
    speed_0_75x = "0.75×",
    speed_1_0x = "1.0×",
    speed_1_25x = "1.25×",
    speed_1_5x = "1.5×",
    speed_2_0x = "2.0×",
    
    -- Errors
    error_title = "Ошибка",
    error_audio_load = "Не удалось загрузить аудиофайл",
    error_manifest_load = "Не удалось загрузить манифест",
    error_playback = "Ошибка воспроизведения",
    error_file_not_found = "Файл не найден",
    error_bluetooth = "Ошибка Bluetooth",
    
    -- Confirmations
    confirm_reset = "Сбросить все настройки к значениям по умолчанию?",
    confirm_close = "Закрыть плеер?",
    
    -- Time format
    time_format = "%02d:%02d",
    time_remaining = "Осталось: %s",
    time_elapsed = "Прошло: %s",
}
