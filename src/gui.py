import sys
import threading
import asyncio
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTextEdit
)
from PyQt6.QtCore import pyqtSignal, QObject

# Import the refactored scraper
from nodriver_scraper import run_scraper

class ScraperSignals(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

class InstagramScraperGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instagram Hashtag Scraper")
        self.resize(500, 400)
        self.signals = ScraperSignals()
        self.signals.log_signal.connect(self.append_log)
        self.signals.finished_signal.connect(self.on_scrape_finished)
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Hashtag Input
        hashtag_layout = QHBoxLayout()
        hashtag_label = QLabel("Hashtag (without #):")
        self.hashtag_input = QLineEdit("wisatalampungselatan")
        hashtag_layout.addWidget(hashtag_label)
        hashtag_layout.addWidget(self.hashtag_input)
        layout.addLayout(hashtag_layout)

        # Limit Input
        limit_layout = QHBoxLayout()
        limit_label = QLabel("Post Limit:")
        self.limit_input = QLineEdit("100")
        limit_layout.addWidget(limit_label)
        limit_layout.addWidget(self.limit_input)
        layout.addLayout(limit_layout)

        # Scrape Button
        self.scrape_btn = QPushButton("Start Scraping")
        self.scrape_btn.clicked.connect(self.start_scraping)
        layout.addWidget(self.scrape_btn)

        # Log Output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def append_log(self, text):
        self.log_output.append(text)
        # Scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_scrape_finished(self):
        self.scrape_btn.setEnabled(True)
        self.append_log("\n--- Scraping process completed ---")

    def start_scraping(self):
        hashtag = self.hashtag_input.text().strip()
        limit_text = self.limit_input.text().strip()
        
        try:
            limit = int(limit_text)
        except ValueError:
            self.append_log("Error: Limit must be an integer.")
            return

        if not hashtag:
            self.append_log("Error: Hashtag cannot be empty.")
            return

        self.append_log(f"Starting async scraper thread for #{hashtag} (Limit: {limit})...")
        self.scrape_btn.setEnabled(False)

        # Run async scraper in a background thread to avoid freezing GUI
        threading.Thread(target=self.run_async_scraper, args=(hashtag, limit), daemon=True).start()

    def run_async_scraper(self, hashtag, limit):
        # We need a new event loop for this background thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # We pass self.signals.log_signal.emit as the callback for print/logging
            loop.run_until_complete(run_scraper(hashtag, limit, self.signals.log_signal.emit))
        except Exception as e:
            self.signals.log_signal.emit(f"Critial Error: {e}")
        finally:
            self.signals.finished_signal.emit()
            loop.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InstagramScraperGUI()
    window.show()
    sys.exit(app.exec())
