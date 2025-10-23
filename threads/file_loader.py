from PyQt5.QtCore import QThread, pyqtSignal


class FileLoaderThread(QThread):
    """Асинхронно читает файл с диска и сообщает результат через сигналы.

    Сигналы:
    - file_loaded(path: str, content: str): успешная загрузка
    - error_occurred(msg: str): ошибка чтения
    - progress_updated(value: int): обновление прогресса (0-100)
    """
    file_loaded = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)

    def __init__(self, file_path):
        """Создает поток загрузки для указанного пути к файлу."""
        super().__init__()
        self.file_path = file_path

    def run(self):
        """Точка входа потока: читает файл и эмитит соответствующие сигналы."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            self.progress_updated.emit(100)
            self.file_loaded.emit(self.file_path, content)
        except Exception as e:
            self.error_occurred.emit(str(e))


