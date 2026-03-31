-- KOReader Plugin Manifest for Luduan Audiobook
return {
    name = "Luduan Audiobook",
    description = "Play synchronized audio with translations for Luduan-generated audiobooks",
    author = "Luduan Team",
    version = "1.0.0",
    min_koreader_version = "2024.01",
    id = "luduan.koplugin",
    main = "main",
    has_menu = true,
    priority = 50,
    supported_devices = "all",
    permissions = {
        "read_storage",
        "write_storage",
        "audio_playback",
    },
}
