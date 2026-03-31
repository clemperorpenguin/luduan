"""
Luduan GUI - PyQt6 based graphical interface for the EPUB to Audiobook pipeline.
"""

import sys
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QProgressBar,
    QTextEdit, QGroupBox, QFormLayout, QComboBox, QCheckBox,
    QTabWidget, QSpinBox, QDoubleSpinBox, QFrame, QSplitter,
    QListWidget, QListWidgetItem, QMessageBox, QSystemTrayIcon,
    QMenu, QAction, QStatusBar, QToolBar, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QUrl, QSettings
)
from PyQt6.QtGui import (
    QIcon, QFont, QColor, QPalette, QAction, QDesktopServices
)

from config import config
from main import LuduanPipeline, find_epub_files


class LogHandler:
    """Custom log handler that emits signals for GUI updates."""
    
    def __init__(self):
        self.logs = []
        self.max_logs = 1000
    
    def add_log(self, level: str, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.logs.append(log_entry)
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
        return log_entry
    
    def get_logs(self) -> list:
        return self.logs
    
    def clear(self):
        self.logs.clear()


# Global log handler
log_handler = LogHandler()


class PipelineWorker(QThread):
    """Background worker thread for running the pipeline."""
    
    # Signals
    log_signal = pyqtSignal(str, str)  # level, message
    progress_signal = pyqtSignal(int)  # percentage
    status_signal = pyqtSignal(str)  # status message
    phase_signal = pyqtSignal(str)  # current phase
    finished_signal = pyqtSignal(bool)  # success
    vram_signal = pyqtSignal(str)  # VRAM info
    
    def __init__(self, epub_path: Path, target_language: str, 
                 translation_only: bool = False, audio_only: bool = False):
        super().__init__()
        self.epub_path = epub_path
        self.target_language = target_language
        self.translation_only = translation_only
        self.audio_only = audio_only
        self.pipeline: Optional[LuduanPipeline] = None
        self._stop_requested = False
    
    def run(self):
        """Execute the pipeline."""
        try:
            self.pipeline = LuduanPipeline(self.epub_path, self.target_language)
            
            # Monkey-patch logger to capture output
            import logger as logger_module
            
            original_info = logger_module.logger.info
            original_error = logger_module.logger.error
            original_warning = logger_module.logger.warning
            original_debug = logger_module.logger.debug
            
            def patched_info(msg):
                self.log_signal.emit("INFO", str(msg))
                original_info(msg)
            
            def patched_error(msg):
                self.log_signal.emit("ERROR", str(msg))
                original_error(msg)
            
            def patched_warning(msg):
                self.log_signal.emit("WARNING", str(msg))
                original_warning(msg)
            
            def patched_debug(msg):
                self.log_signal.emit("DEBUG", str(msg))
                original_debug(msg)
            
            logger_module.logger.info = patched_info
            logger_module.logger.error = patched_error
            logger_module.logger.warning = patched_warning
            logger_module.logger.debug = patched_debug
            
            # Run pipeline
            if self.translation_only:
                success = self.pipeline.run_translation_only()
            elif self.audio_only:
                success = self.pipeline.run_audio_only()
            else:
                success = self.pipeline.run_full_pipeline()
            
            self.finished_signal.emit(success)
            
        except Exception as e:
            self.log_signal.emit("ERROR", str(e))
            self.finished_signal.emit(False)
    
    def stop(self):
        """Request pipeline to stop."""
        self._stop_requested = True


class SettingsDialog(QDialog):
    """Dialog for configuring pipeline settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Paths tab
        tabs = QTabWidget()
        
        # Paths page
        paths_widget = QWidget()
        paths_layout = QFormLayout(paths_widget)
        
        self.input_dir_edit = QLineEdit(str(config.paths.input_dir))
        self.input_dir_edit.setReadOnly(True)
        input_btn = QPushButton("Browse...")
        input_btn.clicked.connect(lambda: self.browse_dir(self.input_dir_edit))
        
        row = QHBoxLayout()
        row.addWidget(self.input_dir_edit)
        row.addWidget(input_btn)
        paths_layout.addRow("Input Directory:", row)
        
        self.output_dir_edit = QLineEdit(str(config.paths.output_dir))
        self.output_dir_edit.setReadOnly(True)
        output_btn = QPushButton("Browse...")
        output_btn.clicked.connect(lambda: self.browse_dir(self.output_dir_edit))
        
        row = QHBoxLayout()
        row.addWidget(self.output_dir_edit)
        row.addWidget(output_btn)
        paths_layout.addRow("Output Directory:", row)
        
        self.cache_dir_edit = QLineEdit(str(config.paths.cache_dir))
        self.cache_dir_edit.setReadOnly(True)
        cache_btn = QPushButton("Browse...")
        cache_btn.clicked.connect(lambda: self.browse_dir(self.cache_dir_edit))
        
        row = QHBoxLayout()
        row.addWidget(self.cache_dir_edit)
        row.addWidget(cache_btn)
        paths_layout.addRow("Cache Directory:", row)
        
        tabs.addTab(paths_widget, "Paths")
        
        # Models page
        models_widget = QWidget()
        models_layout = QFormLayout(models_widget)
        
        self.translation_model_edit = QLineEdit(config.translation.model_name)
        models_layout.addRow("Translation Model:", self.translation_model_edit)
        
        self.tts_model_edit = QLineEdit(config.audio.tts_model_name)
        models_layout.addRow("TTS Model:", self.tts_model_edit)
        
        self.aligner_model_edit = QLineEdit(config.audio.aligner_model_name)
        models_layout.addRow("Aligner Model:", self.aligner_model_edit)
        
        tabs.addTab(models_widget, "Models")
        
        # Processing page
        processing_widget = QWidget()
        processing_layout = QFormLayout(processing_widget)
        
        self.resume_check = QCheckBox("Enable Resume")
        self.resume_check.setChecked(config.processing.enable_resume)
        processing_layout.addRow(self.resume_check)
        
        self.unload_check = QCheckBox("Unload Models Between Phases")
        self.unload_check.setChecked(config.processing.unload_models_between_phases)
        processing_layout.addRow(self.unload_check)
        
        self.min_length_spin = QSpinBox()
        self.min_length_spin.setRange(1, 1000)
        self.min_length_spin.setValue(config.processing.min_paragraph_length)
        processing_layout.addRow("Min Paragraph Length:", self.min_length_spin)
        
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 32)
        self.batch_size_spin.setValue(config.translation.batch_size)
        processing_layout.addRow("Batch Size:", self.batch_size_spin)
        
        tabs.addTab(processing_widget, "Processing")
        
        layout.addWidget(tabs)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def browse_dir(self, line_edit: QLineEdit):
        """Open directory browser."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Directory", line_edit.text()
        )
        if dir_path:
            line_edit.setText(dir_path)
    
    def load_settings(self):
        """Load current settings."""
        pass  # Already set in constructor
    
    def save_settings(self):
        """Save settings to config."""
        config.paths.input_dir = Path(self.input_dir_edit.text())
        config.paths.output_dir = Path(self.output_dir_edit.text())
        config.paths.cache_dir = Path(self.cache_dir_edit.text())
        
        config.translation.model_name = self.translation_model_edit.text()
        config.audio.tts_model_name = self.tts_model_edit.text()
        config.audio.aligner_model_name = self.aligner_model_edit.text()
        
        config.processing.enable_resume = self.resume_check.isChecked()
        config.processing.unload_models_between_phases = self.unload_check.isChecked()
        config.processing.min_paragraph_length = self.min_length_spin.getValue()
        config.translation.batch_size = self.batch_size_spin.getValue()
        
        self.accept()


class LuduanGUI(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.worker: Optional[PipelineWorker] = None
        self.selected_files: list[Path] = []
        self.current_file_index = 0
        
        self.setup_ui()
        self.load_window_settings()
    
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Luduan - EPUB to Audiobook Converter")
        self.setMinimumSize(900, 700)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Toolbar
        self.setup_toolbar()
        
        # File selection
        file_group = QGroupBox("EPUB Files")
        file_layout = QHBoxLayout(file_group)
        
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        file_layout.addWidget(self.file_list, 1)
        
        file_btn_layout = QVBoxLayout()
        
        self.add_file_btn = QPushButton("Add Files")
        self.add_file_btn.clicked.connect(self.add_files)
        file_btn_layout.addWidget(self.add_file_btn)
        
        self.remove_file_btn = QPushButton("Remove Selected")
        self.remove_file_btn.clicked.connect(self.remove_selected_files)
        file_btn_layout.addWidget(self.remove_file_btn)
        
        self.clear_files_btn = QPushButton("Clear All")
        self.clear_files_btn.clicked.connect(self.clear_files)
        file_btn_layout.addWidget(self.clear_files_btn)
        
        file_btn_layout.addStretch()
        file_layout.addLayout(file_btn_layout)
        
        main_layout.addWidget(file_group)
        
        # Settings panel
        settings_group = QGroupBox("Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.language_combo = QComboBox()
        languages = [
            "English", "Chinese", "Japanese", "Korean", 
            "French", "German", "Spanish", "Russian"
        ]
        self.language_combo.addItems(languages)
        settings_layout.addRow("Target Language:", self.language_combo)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Full Pipeline (Translate + Audio)",
            "Translation Only",
            "Audio Only (from existing translation)"
        ])
        settings_layout.addRow("Processing Mode:", self.mode_combo)
        
        settings_row = QHBoxLayout()
        self.resume_check = QCheckBox("Enable Resume")
        self.resume_check.setChecked(config.processing.enable_resume)
        settings_row.addWidget(self.resume_check)
        
        self.tray_check = QCheckBox("Notify on Complete")
        self.tray_check.setChecked(True)
        settings_row.addWidget(self.tray_check)
        
        settings_row.addStretch()
        settings_layout.addRow(settings_row)
        
        main_layout.addWidget(settings_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight: bold;")
        progress_layout.addWidget(self.status_label)
        
        self.phase_label = QLabel("Phase: Idle")
        progress_layout.addWidget(self.phase_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.vram_label = QLabel("VRAM: --")
        progress_layout.addWidget(self.vram_label)
        
        main_layout.addWidget(progress_group)
        
        # Log output
        log_group = QGroupBox("Log Output")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        log_btn_layout = QHBoxLayout()
        
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.clicked.connect(self.clear_log)
        log_btn_layout.addWidget(self.clear_log_btn)
        
        self.save_log_btn = QPushButton("Save Log")
        self.save_log_btn.clicked.connect(self.save_log)
        log_btn_layout.addWidget(self.save_log_btn)
        
        log_btn_layout.addStretch()
        log_layout.addLayout(log_btn_layout)
        
        main_layout.addWidget(log_group, 1)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ Start Processing")
        self.start_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "padding: 10px 30px; font-size: 14px; font-weight: bold; }"
        )
        self.start_btn.clicked.connect(self.start_processing)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; "
            "padding: 10px 30px; font-size: 14px; }"
        )
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        control_layout.addWidget(self.settings_btn)
        
        self.open_output_btn = QPushButton("📁 Open Output Folder")
        self.open_output_btn.clicked.connect(self.open_output_folder)
        control_layout.addWidget(self.open_output_btn)
        
        main_layout.addLayout(control_layout)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def setup_toolbar(self):
        """Set up toolbar."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        add_action = QAction("Add Files", self)
        add_action.triggered.connect(self.add_files)
        toolbar.addAction(add_action)
        
        toolbar.addSeparator()
        
        start_action = QAction("▶ Start", self)
        start_action.triggered.connect(self.start_processing)
        toolbar.addAction(start_action)
        
        stop_action = QAction("⏹ Stop", self)
        stop_action.triggered.connect(self.stop_processing)
        toolbar.addAction(stop_action)
        
        toolbar.addSeparator()
        
        settings_action = QAction("⚙ Settings", self)
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)
        
        about_action = QAction("ℹ About", self)
        about_action.triggered.connect(self.show_about)
        toolbar.addAction(about_action)
    
    def add_files(self):
        """Add EPUB files to the list."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select EPUB Files", 
            str(config.paths.input_dir),
            "EPUB Files (*.epub *.EPUB);;All Files (*)"
        )
        
        for file_path in files:
            path = Path(file_path)
            if path not in self.selected_files:
                self.selected_files.append(path)
                item = QListWidgetItem(path.name)
                item.setToolTip(str(path))
                self.file_list.addItem(item)
        
        if self.selected_files:
            self.statusBar().showMessage(
                f"{len(self.selected_files)} file(s) selected"
            )
    
    def remove_selected_files(self):
        """Remove selected files from the list."""
        selected_items = self.file_list.selectedItems()
        for item in selected_items:
            row = self.file_list.row(item)
            self.file_list.takeItem(row)
            if row < len(self.selected_files):
                self.selected_files.pop(row)
    
    def clear_files(self):
        """Clear all files from the list."""
        self.file_list.clear()
        self.selected_files.clear()
        self.statusBar().showMessage("Ready")
    
    def start_processing(self):
        """Start the pipeline processing."""
        if not self.selected_files:
            QMessageBox.warning(
                self, "No Files", 
                "Please select at least one EPUB file to process."
            )
            return
        
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(
                self, "Already Running",
                "Processing is already in progress."
            )
            return
        
        # Get settings
        target_language = self.language_combo.currentText()
        mode_index = self.mode_combo.currentIndex()
        translation_only = mode_index == 1
        audio_only = mode_index == 2
        
        config.processing.enable_resume = self.resume_check.isChecked()
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.add_file_btn.setEnabled(False)
        self.remove_file_btn.setEnabled(False)
        self.clear_files_btn.setEnabled(False)
        
        self.current_file_index = 0
        self.process_next_file(target_language, translation_only, audio_only)
    
    def process_next_file(self, target_language: str, 
                         translation_only: bool, audio_only: bool):
        """Process the next file in the queue."""
        if self.current_file_index >= len(self.selected_files):
            self.processing_complete()
            return
        
        epub_path = self.selected_files[self.current_file_index]
        self.status_label.setText(f"Processing: {epub_path.name}")
        
        # Create and start worker
        self.worker = PipelineWorker(
            epub_path, target_language, 
            translation_only, audio_only
        )
        
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.status_signal.connect(self.update_status)
        self.worker.phase_signal.connect(self.update_phase)
        self.worker.finished_signal.connect(
            lambda success: self.on_file_complete(success, target_language, 
                                                   translation_only, audio_only)
        )
        self.worker.vram_signal.connect(self.update_vram)
        
        self.worker.start()
    
    def on_file_complete(self, success: bool, target_language: str,
                        translation_only: bool, audio_only: bool):
        """Handle completion of a single file."""
        self.current_file_index += 1
        self.process_next_file(target_language, translation_only, audio_only)
    
    def processing_complete(self):
        """Handle completion of all files."""
        self.stop_btn.setEnabled(False)
        self.start_btn.setEnabled(True)
        self.add_file_btn.setEnabled(True)
        self.remove_file_btn.setEnabled(True)
        self.clear_files_btn.setEnabled(True)
        
        self.status_label.setText("Processing Complete")
        self.progress_bar.setValue(100)
        
        if self.tray_check.isChecked():
            self.show_notification("Processing Complete", 
                                  "All files have been processed.")
        
        self.statusBar().showMessage("Processing complete")
    
    def stop_processing(self):
        """Stop the current processing."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.add_file_btn.setEnabled(True)
            self.remove_file_btn.setEnabled(True)
            self.clear_files_btn.setEnabled(True)
            
            self.status_label.setText("Stopped by User")
            self.append_log("WARNING", "Processing stopped by user")
    
    def update_progress(self, value: int):
        """Update progress bar."""
        self.progress_bar.setValue(value)
    
    def update_status(self, message: str):
        """Update status label."""
        self.status_label.setText(message)
        self.statusBar().showMessage(message)
    
    def update_phase(self, phase: str):
        """Update phase label."""
        self.phase_label.setText(f"Phase: {phase.upper()}")
    
    def update_vram(self, vram_info: str):
        """Update VRAM display."""
        self.vram_label.setText(f"VRAM: {vram_info}")
    
    def append_log(self, level: str, message: str):
        """Append a log message to the text widget."""
        log_entry = log_handler.add_log(level, message)
        
        # Color code log levels
        if level == "ERROR":
            color = "#f44336"
        elif level == "WARNING":
            color = "#ff9800"
        elif level == "INFO":
            color = "#4CAF50"
        else:
            color = "#9e9e9e"
        
        self.log_text.append(
            f'<span style="color: {color};">{log_entry}</span>'
        )
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """Clear the log output."""
        self.log_text.clear()
        log_handler.clear()
    
    def save_log(self):
        """Save log to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Log", 
            str(config.paths.output_dir / "luduan_log.txt"),
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(log_handler.get_logs()))
            
            QMessageBox.information(
                self, "Log Saved", 
                f"Log saved to:\n{file_path}"
            )
    
    def show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self)
        dialog.exec()
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About Luduan",
            "<h2>Luduan - EPUB to Audiobook Converter</h2>"
            "<p>Version 1.0.0</p>"
            "<p>A modular pipeline for converting EPUB books "
            "(especially Chinese web novels) into audiobooks with "
            "KOReader-compatible audio sidecar files.</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Multi-phase architecture</li>"
            "<li>VRAM-optimized processing</li>"
            "<li>Resume capability</li>"
            "<li>Wuxia/Xianxia aware translation</li>"
            "</ul>"
            "<p>© 2024</p>"
        )
    
    def open_output_folder(self):
        """Open the output folder in file manager."""
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(config.paths.output_dir))
        )
    
    def show_notification(self, title: str, message: str):
        """Show system tray notification."""
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        # Create tray icon if needed
        if not hasattr(self, 'tray_icon'):
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(
                self.style().standardIcon(
                    QSystemTrayIcon.StandardIcon.ComputerIcon
                )
            )
            self.tray_icon.show()
        
        self.tray_icon.showMessage(title, message, 
                                   QSystemTrayIcon.MessageIcon.Information,
                                   5000)
    
    def load_window_settings(self):
        """Load window geometry and settings."""
        settings = QSettings("Luduan", "LuduanGUI")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def save_window_settings(self):
        """Save window geometry and settings."""
        settings = QSettings("Luduan", "LuduanGUI")
        settings.setValue("geometry", self.saveGeometry())
    
    def closeEvent(self, event):
        """Handle window close."""
        # Stop any running processing
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Processing in Progress",
                "Processing is still running. Are you sure you want to quit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.stop()
                self.worker.wait()
            else:
                event.ignore()
                return
        
        self.save_window_settings()
        event.accept()


def main():
    """Main entry point for the GUI."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Luduan")
    app.setOrganizationName("Luduan")
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    window = LuduanGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
