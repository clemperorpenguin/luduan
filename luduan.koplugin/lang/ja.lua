-- Japanese (日本語) UI Strings for Luduan Plugin
return {
    -- Plugin name
    plugin_name = "鹿端オーディオブック",
    
    -- Menu items
    menu_enable = "鹿端を有効化",
    menu_disable = "鹿端を無効化",
    menu_settings = "鹿端の設定...",
    menu_play = "オーディオを再生",
    menu_pause = "一時停止",
    menu_stop = "停止",
    menu_next = "次の段落",
    menu_prev = "前の段落",
    
    -- Status messages
    status_playing = "再生中...",
    status_paused = "一時停止中",
    status_stopped = "停止中",
    status_loading = "読み込み中...",
    status_no_audio = "この本のオーディオはありません",
    status_no_translation = "翻訳はありません",
    status_tts_mode = "TTS モード",
    status_bluetooth_connected = "Bluetooth 接続済み",
    status_bluetooth_disconnected = "Bluetooth 切断",
    
    -- Translation display
    translation_label = "翻訳:",
    original_label = "原文:",
    
    -- Controls
    control_play = "再生",
    control_pause = "一時停止",
    control_stop = "停止",
    control_rewind = "10 秒戻る",
    control_forward = "10 秒進む",
    control_speed = "速度",
    control_close = "閉じる",
    control_settings = "設定",
    
    -- Settings dialog
    settings_title = "鹿端の設定",
    settings_playback = "再生",
    settings_display = "表示",
    settings_highlight = "ハイライト",
    settings_language = "言語",
    settings_advanced = "詳細",
    
    -- Playback settings
    setting_auto_play = "タップで自動再生",
    setting_auto_play_desc = "段落をタップしたときに自動的に再生を開始",
    setting_playback_speed = "再生速度",
    setting_volume_boost = "音量ブースト",
    setting_bluetooth_only = "Bluetooth のみ",
    setting_bluetooth_only_desc = "Bluetooth 接続時のみオーディオを再生",
    
    -- Display settings
    setting_show_translation = "翻訳を表示",
    setting_translation_position = "翻訳の位置",
    setting_position_overlay = "オーバーレイ",
    setting_position_bottom = "ボトムパネル",
    setting_position_top = "トップパネル",
    setting_font_size = "フォントサイズ",
    setting_font_family = "フォントファミリー",
    setting_opacity = "不透明度",
    
    -- Highlight settings
    setting_enable_highlight = "ハイライトを有効化",
    setting_highlight_color = "ハイライト色",
    setting_highlight_opacity = "ハイライト不透明度",
    setting_animate_highlight = "ハイライトアニメーション",
    
    -- Language settings
    setting_ui_language = "インターフェース言語",
    setting_preferred_translation = "優先する翻訳",
    setting_tts_fallback = "TTS フォールバック",
    setting_tts_fallback_desc = "翻訳がない場合にテキスト読み上げを使用",
    
    -- Advanced settings
    setting_tap_to_pause = "タップで一時停止/再開",
    setting_auto_scroll = "自動スクロール",
    setting_auto_scroll_desc = "現在の段落を表示し続ける",
    setting_close_on_complete = "完了時に閉じる",
    setting_show_progress = "プログレスバーを表示",
    setting_debug_mode = "デバッグモード",
    
    -- Colors
    color_yellow = "黄色",
    color_green = "緑色",
    color_blue = "青色",
    color_purple = "紫色",
    color_orange = "橙色",
    color_red = "赤色",
    
    -- Speed options
    speed_0_5x = "0.5×",
    speed_0_75x = "0.75×",
    speed_1_0x = "1.0×",
    speed_1_25x = "1.25×",
    speed_1_5x = "1.5×",
    speed_2_0x = "2.0×",
    
    -- Errors
    error_title = "エラー",
    error_audio_load = "オーディオファイルの読み込みに失敗",
    error_manifest_load = "マニフェストの読み込みに失敗",
    error_playback = "再生エラー",
    error_file_not_found = "ファイルが見つかりません",
    error_bluetooth = "Bluetooth エラー",
    
    -- Confirmations
    confirm_reset = "すべての設定をデフォルトにリセットしますか？",
    confirm_close = "プレーヤーを閉じますか？",
    
    -- Time format
    time_format = "%02d:%02d",
    time_remaining = "残り：%s",
    time_elapsed = "経過：%s",
}
