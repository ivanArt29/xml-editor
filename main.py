import sys
import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, QVBoxLayout, 
                             QWidget, QToolBar, QAction, QFileDialog, 
                             QMessageBox, QLabel, QStatusBar, QColorDialog, QTreeWidget, QTreeWidgetItem, QSplitter, QComboBox, QFontComboBox, QAbstractItemView, QProgressBar, QStyle)
from PyQt5.QtGui import QFont, QPalette, QColor, QTextCursor
from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal
from PyQt5.QtGui import QTextOption
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from syntax_highlighter import XmlHighlighter
from settings_dialog import SettingsDialog
from PyQt5.QtWidgets import QDialog
from tree_builder import TreeBuilderThread, ElementTreeBuilderThread
from file_loader import FileLoaderThread

class XMLEditor(QMainWindow):
    """Главное окно XML-редактора: редактор текста, дерево, меню и действия."""
    def __init__(self):
        """Инициализирует состояние, UI и загружает сохранённые настройки."""
        super().__init__()
        self.current_file = None
        # Настройки в INI-файле рядом с приложением
        settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_settings.ini")
        self.settings = QSettings(settings_path, QSettings.IniFormat)
        self.is_dirty = False
        self._suppress_tree_update = False
        self._DUMMY_ROLE = Qt.UserRole + 1
        self._tree_builder_thread = None
        self._file_loader_thread = None
        self._progress_bar = None
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Создаёт и настраивает виджеты, панели, меню и статус-бар."""
        self.setWindowTitle("Текстовый XML-редактор")
        self.setGeometry(100, 100, 1200, 800)
        # Иконка окна
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        
        # Создаем сплиттер с деревом и редактором
        self.splitter = QSplitter(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Элемент", "Значение", "Атрибуты"])
        # По умолчанию делаем столбец атрибутов шире
        self.tree.setColumnWidth(2, 300)
        self.tree.itemClicked.connect(self.on_tree_item_clicked)
        self.tree.itemChanged.connect(self.on_tree_item_changed)
        self.tree.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed)
        self.tree.itemExpanded.connect(self.on_item_expanded)
        self.create_editor()
        self.splitter.addWidget(self.tree)
        self.splitter.addWidget(self.editor)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        # Шире панель дерева по умолчанию
        self.splitter.setSizes([500, 700])
        # Центральная область — старый сплиттер
        self.setCentralWidget(self.splitter)

        # Создание панелей инструментов
        self.create_toolbar()
        self.create_xml_toolbar()
        self.create_tree_actions()

        # Меню/действие Настройки
        self.settings_action = QAction("Настройки", self)
        self.settings_action.setShortcut("Ctrl+,")
        self.settings_action.triggered.connect(self.open_settings_dialog)

        # Недавние файлы (до создания меню)
        self.recent_files = []
        self._load_recent_files()

        # Создаем меню
        self.create_menus()

        # Создание статусной строки
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готово")
        
        # Создание прогресс-бара для больших файлов
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self._progress_bar)
        # Инициализируем заголовок с актуальным состоянием
        self._refresh_window_title()

    def _refresh_window_title(self):
        """Обновляет заголовок окна и добавляет '*' при несохранённых изменениях."""
        base = "Текстовый XML-редактор"
        name = os.path.basename(self.current_file) if self.current_file else "Новый файл"
        star = "*" if self.is_dirty else ""
        self.setWindowTitle(f"{star}{base} - {name}")

    def create_toolbar(self):
        """Создаёт основную панель инструментов и её действия."""
        self.toolbar = QToolBar("Основные инструменты")
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)
        
        # Действия для файлов
        self.new_action = QAction("Новый", self)
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.triggered.connect(self.new_file)
        
        self.open_action = QAction("Открыть", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_file)
        
        self.save_action = QAction("Сохранить", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.save_file)
        
        self.save_as_action = QAction("Сохранить как", self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(self.save_as_file)
        
        self.print_action = QAction("Печать", self)
        self.print_action.setShortcut("Ctrl+P")
        self.print_action.triggered.connect(self.print_file)

        self.export_html_action = QAction("Экспорт в HTML", self)
        self.export_html_action.triggered.connect(self.export_to_html)

        self.export_pdf_action = QAction("Экспорт в PDF", self)
        self.export_pdf_action.triggered.connect(self.export_to_pdf)
        
        # Добавляем действия на панель
        self.toolbar.addAction(self.new_action)
        self.toolbar.addAction(self.open_action)
        self.toolbar.addAction(self.save_action)
        self.toolbar.addAction(self.save_as_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.print_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.export_html_action)
        self.toolbar.addAction(self.export_pdf_action)

        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        
    def create_xml_toolbar(self):
        """Создаёт панель инструментов для операций с XML."""
        self.xml_toolbar = QToolBar("XML")
        self.xml_toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)

        self.validate_action = QAction("Проверить XML", self)
        self.validate_action.setShortcut("F7")
        self.validate_action.triggered.connect(self.validate_xml)

        self.pretty_action = QAction("Форматировать XML", self)
        self.pretty_action.setShortcut("Ctrl+Shift+F")
        self.pretty_action.triggered.connect(self.pretty_format_xml)

        self.wrap_action = QAction("Перенос строк", self)
        self.wrap_action.setCheckable(True)
        self.wrap_action.setChecked(False)
        self.wrap_action.toggled.connect(self.toggle_word_wrap)

        self.xml_toolbar.addAction(self.validate_action)
        self.xml_toolbar.addAction(self.pretty_action)
        self.xml_toolbar.addSeparator()
        self.xml_toolbar.addAction(self.wrap_action)

        self.addToolBar(Qt.TopToolBarArea, self.xml_toolbar)

    def create_tree_actions(self):
        """Создаёт панель инструментов для управления деревом XML."""
        self.tree_toolbar = QToolBar("Структура")
        self.tree_toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)

        self.toggle_tree_action = QAction("Показать/скрыть дерево", self)
        self.toggle_tree_action.setCheckable(True)
        self.toggle_tree_action.setChecked(True)
        self.toggle_tree_action.toggled.connect(self.toggle_tree)

        self.refresh_tree_action = QAction("Обновить дерево", self)
        self.refresh_tree_action.setShortcut("F5")
        self.refresh_tree_action.triggered.connect(self.build_tree_from_editor)

        self.tree_toolbar.addAction(self.toggle_tree_action)
        self.tree_toolbar.addAction(self.refresh_tree_action)
        self.addToolBar(Qt.TopToolBarArea, self.tree_toolbar)

    
    
    def create_menus(self):
        """Создаёт строки меню, их пункты и подменю."""
        menubar = self.menuBar()
        # Файл
        self.file_menu = menubar.addMenu("Файл")
        self.file_menu.addAction(self.new_action)
        self.file_menu.addAction(self.open_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.save_action)
        self.file_menu.addAction(self.save_as_action)

        # Недавние файлы
        self.recent_menu = self.file_menu.addMenu("Недавние файлы")
        self._rebuild_recent_menu()

        self.file_menu.addSeparator()
        self.file_menu.addAction(self.print_action)
        # Закрытие
        exit_action = QAction("Закрыть", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        self.file_menu.addSeparator()
        self.file_menu.addAction(exit_action)

        # Экспорт
        export_menu = menubar.addMenu("Экспорт")
        export_menu.addAction(self.export_html_action)
        export_menu.addAction(self.export_pdf_action)

        # Правка (единый пункт «Найти и заменить...» с диалогом)
        edit_menu = menubar.addMenu("Правка")
        self.find_replace_action = QAction("Найти и заменить...", self)
        self.find_replace_action.setShortcut("Ctrl+F")
        self.find_replace_action.triggered.connect(self.open_find_dialog)
        edit_menu.addAction(self.find_replace_action)

        # XML
        xml_menu = menubar.addMenu("XML")
        xml_menu.addAction(self.validate_action)
        xml_menu.addAction(self.pretty_action)
        xml_menu.addSeparator()
        xml_menu.addAction(self.wrap_action)

        # Структура
        structure_menu = menubar.addMenu("Структура")
        structure_menu.addAction(self.toggle_tree_action)
        structure_menu.addAction(self.refresh_tree_action)

        # Настройки
        settings_menu = menubar.addMenu("Настройки")
        settings_menu.addAction(self.settings_action)
        
        # О программе
        about_menu = menubar.addMenu("О программе")
        self.about_action = QAction("О программе", self)
        self.about_action.triggered.connect(self.show_about_dialog)
        about_menu.addAction(self.about_action)

        # Скрыть панели инструментов (убрать дублирование кнопок)
        self.toolbar.setVisible(False)
        self.xml_toolbar.setVisible(False)
        self.tree_toolbar.setVisible(False)

    def open_find_dialog(self):
        # Модальное окно поиска/замены, как в блокноте
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Поиск и замена")
        layout = QVBoxLayout(dlg)

        row_find = QHBoxLayout()
        row_find.addWidget(QLabel("Найти:"))
        find_input = QLineEdit()
        row_find.addWidget(find_input)
        case_cb = QCheckBox("Регистр")
        whole_cb = QCheckBox("Целое слово")
        row_find.addWidget(case_cb)
        row_find.addWidget(whole_cb)
        layout.addLayout(row_find)

        row_replace = QHBoxLayout()
        row_replace.addWidget(QLabel("Заменить на:"))
        replace_input = QLineEdit()
        row_replace.addWidget(replace_input)
        layout.addLayout(row_replace)

        row_btns = QHBoxLayout()
        find_next_btn = QPushButton("Найти далее")
        find_prev_btn = QPushButton("Найти назад")
        replace_btn = QPushButton("Заменить")
        replace_all_btn = QPushButton("Заменить все")
        close_btn = QPushButton("Закрыть")
        row_btns.addWidget(find_next_btn)
        row_btns.addWidget(find_prev_btn)
        row_btns.addWidget(replace_btn)
        row_btns.addWidget(replace_all_btn)
        row_btns.addWidget(close_btn)
        layout.addLayout(row_btns)

        def build_flags():
            from PyQt5.QtGui import QTextDocument
            flags = QTextDocument.FindFlags()
            if case_cb.isChecked():
                flags |= QTextDocument.FindCaseSensitively
            if whole_cb.isChecked():
                flags |= QTextDocument.FindWholeWords
            return flags

        def do_find(forward: bool):
            from PyQt5.QtGui import QTextDocument
            pattern = find_input.text()
            if not pattern:
                return
            flags = build_flags()
            if not forward:
                flags |= QTextDocument.FindBackward
            self.editor.find(pattern, flags)

        def do_replace_once():
            cursor = self.editor.textCursor()
            if not cursor.hasSelection():
                do_find(True)
                cursor = self.editor.textCursor()
                if not cursor.hasSelection():
                    return
            cursor.insertText(replace_input.text())
            self.is_dirty = True
            do_find(True)

        def do_replace_all():
            pattern = find_input.text()
            if not pattern:
                return
            replacement = replace_input.text()
            text = self.editor.toPlainText()
            new_text = text.replace(pattern, replacement)
            count = text.count(pattern)
            if count > 0:
                self.editor.blockSignals(True)
                self.editor.setPlainText(new_text)
                self.editor.blockSignals(False)
                self.is_dirty = True
                self.status_bar.showMessage(f"Заменено: {count}")

        find_next_btn.clicked.connect(lambda: do_find(True))
        find_prev_btn.clicked.connect(lambda: do_find(False))
        replace_btn.clicked.connect(do_replace_once)
        replace_all_btn.clicked.connect(do_replace_all)
        close_btn.clicked.connect(dlg.close)

        dlg.setModal(True)
        dlg.resize(600, 140)
        dlg.show()
        
    def create_editor(self):
        """Создаёт основной текстовый редактор и подключает подсветку."""
        self.editor = QPlainTextEdit()
        self.editor.textChanged.connect(self.on_text_changed)
        self.editor.cursorPositionChanged.connect(self.update_status)
        self.editor.setWordWrapMode(QTextOption.NoWrap)
        
        # Начальные настройки по умолчанию; будут переопределены из настроек
        self.editor.setFont(QFont("Consolas", 12))

        # Подсветка синтаксиса XML
        self.highlighter = XmlHighlighter(self.editor.document())

    def _build_search_tab(self, parent_widget):
        from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QCheckBox, QLabel
        layout = QVBoxLayout(parent_widget)

        # Строка поиска
        row_find = QHBoxLayout()
        row_find.addWidget(QLabel("Найти:"))
        self.find_input = QLineEdit()
        row_find.addWidget(self.find_input)
        self.case_cb = QCheckBox("Регистр")
        row_find.addWidget(self.case_cb)
        self.whole_cb = QCheckBox("Целое слово")
        row_find.addWidget(self.whole_cb)
        self.find_next_btn = QPushButton("Найти далее")
        self.find_prev_btn = QPushButton("Найти назад")
        row_find.addWidget(self.find_next_btn)
        row_find.addWidget(self.find_prev_btn)
        layout.addLayout(row_find)

        # Строка замены
        row_replace = QHBoxLayout()
        row_replace.addWidget(QLabel("Заменить на:"))
        self.replace_input = QLineEdit()
        row_replace.addWidget(self.replace_input)
        self.replace_btn = QPushButton("Заменить")
        self.replace_all_btn = QPushButton("Заменить все")
        row_replace.addWidget(self.replace_btn)
        row_replace.addWidget(self.replace_all_btn)
        layout.addLayout(row_replace)

        # Связи
        self.find_next_btn.clicked.connect(lambda: self._find(forward=True))
        self.find_prev_btn.clicked.connect(lambda: self._find(forward=False))
        self.replace_btn.clicked.connect(self._replace_once)
        self.replace_all_btn.clicked.connect(self._replace_all)

    def _build_find_flags(self):
        from PyQt5.QtGui import QTextDocument
        flags = QTextDocument.FindFlags()
        if self.case_cb.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        if self.whole_cb.isChecked():
            flags |= QTextDocument.FindWholeWords
        return flags

    def _find(self, forward: bool):
        from PyQt5.QtGui import QTextDocument
        pattern = self.find_input.text()
        if not pattern:
            return
        flags = self._build_find_flags()
        if not forward:
            flags |= QTextDocument.FindBackward
        self.editor.find(pattern, flags)

    def _select_range(self, start: int, end: int):
        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()

    def _replace_once(self):
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            self._find(forward=True)
            cursor = self.editor.textCursor()
            if not cursor.hasSelection():
                return
        replacement = self.replace_input.text()
        cursor.insertText(replacement)
        self.is_dirty = True
        # перейти к следующему
        self._find(forward=True)

    def _replace_all(self):
        from PyQt5.QtGui import QTextDocument
        pattern = self.find_input.text()
        if not pattern:
            return
        replacement = self.replace_input.text()

        doc = self.editor.document()
        flags = self._build_find_flags()
        # Для replace all всегда идём вперёд
        flags &= ~QTextDocument.FindBackward

        count = 0
        self.editor.blockSignals(True)
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        try:
            pos = 0
            while True:
                hit = doc.find(pattern, pos, flags)
                if hit.isNull():
                    break
                hit.insertText(replacement)
                pos = hit.position()
                count += 1
        finally:
            cursor.endEditBlock()
            self.editor.blockSignals(False)

        if count:
            self.is_dirty = True
            self.status_bar.showMessage(f"Заменено: {count}")
    
    def new_file(self):
        """Очищает редактор и начинает новый документ."""
        if not self.confirm_save_if_dirty():
            return
        self.editor.clear()
        self.current_file = None
        self.is_dirty = False
        self._refresh_window_title()
        self.status_bar.showMessage("Создан новый файл")
        self.tree.clear()
        
    def open_file(self):
        """Открывает файл через диалог и запускает асинхронную загрузку."""
        if not self.confirm_save_if_dirty():
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть XML файл", "", "XML Files (*.xml);;All Files (*)")
        
        if file_path:
            self._start_file_loading(file_path)

    def _start_file_loading(self, file_path: str):
        """Запускает поток загрузки файла и настраивает прогресс."""
        # Показываем индикатор загрузки
        self.status_bar.showMessage("Загрузка файла...")
        
        # Останавливаем предыдущий поток загрузки, если он есть
        if self._file_loader_thread and self._file_loader_thread.isRunning():
            self._file_loader_thread.terminate()
            self._file_loader_thread.wait()
        
        # Настройка прогресса
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(50)
        
        # Запускаем загрузку файла в отдельном потоке
        self._file_loader_thread = FileLoaderThread(file_path)
        self._file_loader_thread.file_loaded.connect(self.on_file_loaded)
        self._file_loader_thread.error_occurred.connect(self.on_file_load_error)
        self._file_loader_thread.progress_updated.connect(self.on_file_load_progress)
        self._file_loader_thread.start()
                
    def save_file(self):
        """Сохраняет текущий документ в текущий файл либо предлагает 'Сохранить как'."""
        if self.current_file:
            try:
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(self.editor.toPlainText())
                self.status_bar.showMessage(f"Файл сохранен: {self.current_file}")
                self.is_dirty = False
                self._refresh_window_title()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {str(e)}")
        else:
            self.save_as_file()
            
    def save_as_file(self):
        """Сохраняет текущий документ под новым именем."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XML файл", "", "XML Files (*.xml);;All Files (*)")
        
        if file_path:
            if not file_path.endswith('.xml'):
                file_path += '.xml'
                
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(self.editor.toPlainText())
                
                self.current_file = file_path
                self.is_dirty = False
                self._refresh_window_title()
                self.status_bar.showMessage(f"Файл сохранен: {file_path}")
                self._add_recent_file(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {str(e)}")
                
    def print_file(self):
        """Открывает диалог печати и отправляет документ на принтер/PDF."""
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec_() == QPrintDialog.Accepted:
            # Печать документа редактора
            self.editor.document().print(printer)
            self.status_bar.showMessage("Отправлено на печать")

    def export_to_html(self):
        """Экспортирует текущий текст как HTML"""
        from exporter import export_to_html as _export_to_html
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в HTML", "", "HTML Files (*.html);;All Files (*)")
        if not file_path:
            return
        if not file_path.endswith('.html'):
            file_path += '.html'
        try:
            _export_to_html(
                text=self.editor.toPlainText(),
                font=self.editor.font(),
                palette=self.editor.palette(),
                target_path=file_path,
            )
            self.status_bar.showMessage(f"Экспортировано в HTML: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось сохранить HTML: {str(e)}")

    def export_to_pdf(self):
        """Экспортирует текущий документ в PDF через систему печати."""
        from exporter import export_to_pdf as _export_to_pdf
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в PDF", "", "PDF Files (*.pdf);;All Files (*)")
        if not file_path:
            return
        if not file_path.endswith('.pdf'):
            file_path += '.pdf'
        try:
            _export_to_pdf(self.editor.document(), file_path)
            self.status_bar.showMessage(f"Экспортировано в PDF: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось сохранить PDF: {str(e)}")
            
    def toggle_word_wrap(self, enabled):
        """Включает или выключает перенос строк в редакторе."""
        if enabled:
            self.editor.setWordWrapMode(QTextOption.WordWrap)
        else:
            self.editor.setWordWrapMode(QTextOption.NoWrap)
        self.settings.setValue("appearance/word_wrap", bool(enabled))

    def change_font(self, font):
        """Меняет семейство шрифта редактора и сохраняет в настройки."""
        current = self.editor.font()
        current.setFamily(font.family())
        self.editor.setFont(current)
        self.settings.setValue("appearance/font_family", font.family())

    def change_font_size(self, size):
        """Меняет размер шрифта редактора и сохраняет в настройки."""
        try:
            point_size = float(size)
        except ValueError:
            return
        current = self.editor.font()
        current.setPointSizeF(point_size)
        self.editor.setFont(current)
        self.font_size.setCurrentText(str(int(point_size)))
        self.settings.setValue("appearance/font_size", point_size)

    def toggle_bold(self, checked):
        """Включает/выключает жирность шрифта редактора."""
        current = self.editor.font()
        current.setBold(bool(checked))
        self.editor.setFont(current)
        self.settings.setValue("appearance/font_bold", bool(checked))

    def toggle_italic(self, checked):
        """Включает/выключает курсив в шрифте редактора."""
        current = self.editor.font()
        current.setItalic(bool(checked))
        self.editor.setFont(current)
        self.settings.setValue("appearance/font_italic", bool(checked))

    def toggle_underline(self, checked):
        """Включает/выключает подчеркивание в шрифте редактора."""
        current = self.editor.font()
        current.setUnderline(bool(checked))
        self.editor.setFont(current)
        self.settings.setValue("appearance/font_underline", bool(checked))

    def change_text_color(self):
        """Открывает палитру для выбора цвета текста и применяет его."""
        color = QColorDialog.getColor(parent=self, title="Выберите цвет текста")
        if color.isValid():
            palette = self.editor.palette()
            palette.setColor(QPalette.Text, color)
            self.editor.setPalette(palette)
            # Сохраняем в настройки
            self.settings.setValue("appearance/text_color", color.name())

    def change_bg_color(self):
        """Открывает палитру для выбора цвета фона и применяет его."""
        color = QColorDialog.getColor(parent=self, title="Выберите цвет фона")
        if color.isValid():
            palette = self.editor.palette()
            palette.setColor(QPalette.Base, color)
            self.editor.setPalette(palette)
            # Сохраняем в настройки
            self.settings.setValue("appearance/bg_color", color.name())
            
    def update_status(self):
        """Обновляет строку состояния (строки, символы, позиция курсора)."""
        text = self.editor.toPlainText()
        lines = text.count('\n') + 1
        chars = len(text)

        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        self.status_bar.showMessage(f"Строк: {lines} | Символов: {chars} | Позиция: {line}:{col}")

    def on_text_changed(self):
        """Помечает документ как изменённый и обновляет статус."""
        self.is_dirty = True
        self.update_status()
        self._refresh_window_title()

    def confirm_save_if_dirty(self):
        """Предлагает сохранить изменения; возвращает True, если можно продолжать."""
        if not self.is_dirty or not self.editor.toPlainText().strip():
            return True
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Несохраненные изменения")
        msg.setText("Сохранить изменения в текущем файле?")
        save_btn = msg.addButton("Сохранить", QMessageBox.YesRole)
        discard_btn = msg.addButton("Не сохранять", QMessageBox.NoRole)
        cancel_btn = msg.addButton("Отмена", QMessageBox.RejectRole)
        msg.exec_()
        clicked = msg.clickedButton()
        if clicked == save_btn:
            self.save_file()
            return not self.is_dirty
        if clicked == discard_btn:
            return True
        return False

    def validate_xml(self):
        """Проверяет, что текущий XML корректен синтаксически (well-formed)."""
        xml_text = self.editor.toPlainText()
        try:
            ET.fromstring(xml_text)
            QMessageBox.information(self, "Проверка XML", "XML корректен (well-formed).")
        except ET.ParseError as e:
            QMessageBox.critical(self, "Ошибка XML", f"Некорректный XML:\n{str(e)}")

    def pretty_format_xml(self):
        """Форматирует текущий XML с отступами и обновляет дерево."""
        xml_text = self.editor.toPlainText()
        try:
            # Сначала проверим корректность
            ET.fromstring(xml_text)
            pretty = minidom.parseString(xml_text).toprettyxml(indent="  ")
            pretty_lines = [line for line in pretty.splitlines() if line.strip()]
            self.editor.setPlainText("\n".join(pretty_lines))
            self.is_dirty = True
            self.status_bar.showMessage("XML отформатирован")
            self.build_tree_from_text(self.editor.toPlainText())
        except ET.ParseError as e:
            QMessageBox.critical(self, "Ошибка форматирования", f"XML некорректен:\n{str(e)}")
        
    def load_settings(self):
        """Загружает сохранённые настройки окна, шрифта, цветов и облика."""
        # Загрузка настроек
        geometry = self.settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)

        font_family = self.settings.value("appearance/font_family", "Consolas")
        font_size = float(self.settings.value("appearance/font_size", 12))
        font_bold = self.settings.value("appearance/font_bold", False, type=bool)
        font_italic = self.settings.value("appearance/font_italic", False, type=bool)
        font_underline = self.settings.value("appearance/font_underline", False, type=bool)
        text_color = self.settings.value("appearance/text_color", "#000000")
        bg_color = self.settings.value("appearance/bg_color", "#ffffff")
        wrap = self.settings.value("appearance/word_wrap", False, type=bool)
        tag_color = self.settings.value("appearance/tag_color", "#0066cc")

        f = self.editor.font()
        f.setFamily(font_family)
        f.setPointSizeF(font_size)
        f.setBold(font_bold)
        f.setItalic(font_italic)
        f.setUnderline(font_underline)
        self.editor.setFont(f)

        pal = self.editor.palette()
        pal.setColor(QPalette.Text, QColor(text_color))
        pal.setColor(QPalette.Base, QColor(bg_color))
        self.editor.setPalette(pal)

        self.toggle_word_wrap(wrap)

        # Цвет подсветки тегов
        self.highlighter.set_tag_color(QColor(tag_color))
        # Отображение дерева по умолчанию
        # Ничего не строим до загрузки файла/текста
        
            
    def closeEvent(self, event):
        """Останавливает фоновые потоки и сохраняет состояние перед выходом."""
        # Останавливаем фоновые потоки при закрытии
        if self._tree_builder_thread and self._tree_builder_thread.isRunning():
            self._tree_builder_thread.terminate()
            self._tree_builder_thread.wait()
        if self._file_loader_thread and self._file_loader_thread.isRunning():
            self._file_loader_thread.terminate()
            self._file_loader_thread.wait()
        # Сохранение настроек при закрытии
        if not self.confirm_save_if_dirty():
            event.ignore()
            return
        self.settings.setValue("window/geometry", self.saveGeometry())
        event.accept()

    
    def toggle_tree(self, visible: bool):
        """Показывает или скрывает панель дерева XML."""
        self.tree.setVisible(visible)

    def build_tree_from_editor(self):
        """Строит дерево на основе текущего содержимого редактора."""
        self.build_tree_from_text(self.editor.toPlainText())

    def build_tree_from_text(self, text: str):
        """Асинхронно строит дерево из заданного XML-текста."""
        self.tree.clear()
        if not text.strip():
            return
        
        # Показываем индикатор загрузки
        self.status_bar.showMessage("Построение дерева...")
        
        # Запускаем построение дерева в отдельном потоке
        if self._tree_builder_thread and self._tree_builder_thread.isRunning():
            self._tree_builder_thread.terminate()
            self._tree_builder_thread.wait()
        
        self._tree_builder_thread = TreeBuilderThread(text)
        self._tree_builder_thread.tree_ready.connect(self.on_tree_built)
        self._tree_builder_thread.error_occurred.connect(self.on_tree_build_error)
        self._tree_builder_thread.start()

    

    def _make_item_for_element(self, elem: ET.Element, path_indices) -> QTreeWidgetItem:
        """Создаёт визуальный элемент дерева для XML-узла с иконкой."""
        # Значение элемента (без пробелов по краям)
        value = (elem.text or "").strip()
        attrs = " ".join([f"{k}={v}" for k, v in elem.attrib.items()])
        children = list(elem)
        has_children = bool(children)
        has_text = bool(value)
        has_attrs = bool(elem.attrib)

        #Иконки для узлов дерева
        if has_children:
            prefix = "📦"  # контейнер элемента
        elif has_text and has_attrs:
            prefix = "🧾"  # элемент с данными и атрибутами
        elif has_text:
            prefix = "📝"  # текстовый элемент
        elif has_attrs:
            prefix = "🏷️"  # элемент только с атрибутами
        else:
            prefix = "📄"  # пустой листовой элемент

        item = QTreeWidgetItem([f"{prefix} {elem.tag}", value, attrs])
        # Храним путь до элемента
        item.setData(0, Qt.UserRole, path_indices)
        # Делаем элемент редактируемым
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        # Отложеннное раскрытие детей
        if has_children:
            # Добавляем заглушку для последующей подгрузки дочерних узлов
            dummy = QTreeWidgetItem(["Загрузка…", "", ""])
            dummy.setData(0, self._DUMMY_ROLE, True)
            item.addChild(dummy)
        return item

    def on_tree_item_clicked(self, item: QTreeWidgetItem):
        """Переходит к соответствующему элементу в тексте при клике по дереву."""
        # По клику переходим к соответствующему элементу в тексте
        visual = item.text(0) or ""
        # Элемент формируется как "<эмодзи> <tag>", извлекаем чистое имя тега
        pure_tag = visual.split(" ", 1)[1] if " " in visual else visual
        if not pure_tag or pure_tag == "XML Document":
            return
        #Позиционирование элемент, используя путь индексов
        path_indices = item.data(0, Qt.UserRole)
        if isinstance(path_indices, list):
            pos = self._find_position_for_path(pure_tag, path_indices)
            if pos is not None:
                cursor = self.editor.textCursor()
                cursor.setPosition(pos)
                # Выделим открывающий тег
                end_pos = self.editor.toPlainText().find('>', pos)
                if end_pos != -1:
                    cursor.setPosition(end_pos + 1, QTextCursor.KeepAnchor)
                self.editor.setTextCursor(cursor)
                self.editor.ensureCursorVisible()
                self.status_bar.showMessage(f"Найден элемент: {pure_tag}")
                return
        #Ищем первое вхождение
        self.highlight_element_in_text(pure_tag)

    def _find_position_for_path(self, tag_name: str, path_indices):
        """Находит позицию в тексте для элемента по пути индексов."""
        xml_text = self.editor.toPlainText()
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return None

        # Найти целевой элемент по пути
        target = self._get_element_by_path(root, path_indices)
        if target is None:
            return None

        # Подсчитать порядковый номер целевого тега среди всех элементов с таким же именем
        occurrence = 0
        target_occurrence = None

        def preorder_count(elem):
            nonlocal occurrence, target_occurrence
            if elem.tag == tag_name:
                occurrence += 1
                if elem is target:
                    target_occurrence = occurrence
                    return True  
            for child in list(elem):
                if preorder_count(child):
                    return True
            return False

        preorder_count(root)
        if not target_occurrence:
            return None

        needle = f"<{tag_name}"
        idx = -1
        start = 0
        for _ in range(target_occurrence):
            idx = xml_text.find(needle, start)
            if idx == -1:
                return None
            start = idx + 1
        return idx

    def highlight_element_in_text(self, tag_name):
        """Выделяет первое вхождение открывающего тега в редакторе."""
        text = self.editor.toPlainText()
        # Ищем первое вхождение тега
        start_pos = text.find(f"<{tag_name}")
        if start_pos != -1:
            # Выделяем открывающий тег целиком
            end_pos = text.find('>', start_pos)
            cursor = self.editor.textCursor()
            if end_pos != -1 and end_pos > start_pos:
                cursor.setPosition(start_pos)
                cursor.setPosition(end_pos + 1, QTextCursor.KeepAnchor)
            else:
                cursor.setPosition(start_pos)
            self.editor.setTextCursor(cursor)
            self.editor.ensureCursorVisible()
            self.status_bar.showMessage(f"Найден элемент: {tag_name}")

    def on_tree_item_changed(self, item: QTreeWidgetItem, column: int):
        """Синхронизирует изменение значения в дереве с XML-текстом."""
        if self._suppress_tree_update:
            return
        # Интересует изменение значения (колонка 1)
        if column != 1:
            return
        path_indices = item.data(0, Qt.UserRole)
        if path_indices is None:
            return
        new_value = item.text(1)
        xml_text = self.editor.toPlainText()
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            # Если текущий текст некорректен, откатим визуальное изменение
            self._suppress_tree_update = True
            # Перестроим дерево из текущего текста (ничего не меняем)
            self.build_tree_from_text(xml_text)
            self._suppress_tree_update = False
            QMessageBox.critical(self, "Ошибка XML", "Текущий XML некорректен, изменение невозможно.")
            return

        # Найдем элемент по пути индексов
        target = self._get_element_by_path(root, path_indices)
        if target is None:
            return
        target.text = new_value

        #ОБбратно в текст
        rough = ET.tostring(root, encoding='unicode')
        try:
            pretty = minidom.parseString(rough).toprettyxml(indent="  ")
            pretty_lines = [line for line in pretty.splitlines() if line.strip()]
            new_xml = "\n".join(pretty_lines)
        except Exception:
            new_xml = rough

        self._suppress_tree_update = True
        self.editor.blockSignals(True)
        self.editor.setPlainText(new_xml)
        self.editor.blockSignals(False)
        self.is_dirty = True
        self.status_bar.showMessage("Значение элемента обновлено из дерева")
        # Перестроим дерево из нового текста
        self.build_tree_from_text(new_xml)
        self._suppress_tree_update = False

    def _get_element_by_path(self, root_elem: ET.Element, path_indices):
        """Возвращает потомка по списку индексов детей от корня."""
        elem = root_elem
        for idx in path_indices:
            children = list(elem)
            if idx < 0 or idx >= len(children):
                return None
            elem = children[idx]
        return elem

    def on_item_expanded(self, item: QTreeWidgetItem):
        """Лениво подгружает детей при раскрытии узла, удаляя заглушку."""
        # Если уже подгружено (нет заглушек) — выходим
        if item.childCount() == 0:
            return
        first_child = item.child(0)
        if not first_child.data(0, self._DUMMY_ROLE):
            return

        # Для обычных файлов используем текст редактора
        path_indices = item.data(0, Qt.UserRole) or []
        xml_text = self.editor.toPlainText()
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return
        parent_elem = self._get_element_by_path(root, path_indices)
        if parent_elem is None:
            return

        self._suppress_tree_update = True
        self.tree.blockSignals(True)
        self.tree.setUpdatesEnabled(False)
        try:
            # Удаляем заглушку
            item.takeChild(0)
            # Добавляем реальных детей (только одно «поколение»)
            for idx, child in enumerate(list(parent_elem)):
                child_item = self._make_item_for_element(child, path_indices + [idx])
                item.addChild(child_item)
        finally:
            self.tree.setUpdatesEnabled(True)
            self.tree.blockSignals(False)
            self._suppress_tree_update = False

    def on_tree_built(self, root_item):
        """Добавляет построенное дерево на виджет и завершает обновление UI."""
        self._suppress_tree_update = True
        self.tree.blockSignals(True)
        self.tree.setUpdatesEnabled(False)
        try:
            self.tree.addTopLevelItem(root_item)
            self.status_bar.showMessage("Дерево построено")
        finally:
            self.tree.setUpdatesEnabled(True)
            self.tree.blockSignals(False)
            self._suppress_tree_update = False
        # По умолчанию не раскрываем всё дерево

    def on_tree_build_error(self, error_msg):
        """Показывает ошибку, возникшую при построении дерева."""
        self.status_bar.showMessage("Ошибка построения дерева")
        QMessageBox.critical(self, "Ошибка XML", f"Не удалось построить дерево: {error_msg}")

    def on_file_loaded(self, file_path, content):
        """Заполняет редактор содержимым загруженного файла и строит дерево."""
        # Скрываем прогресс-бар
        self._progress_bar.setVisible(False)
        
        self.current_file = file_path
        
        # Загружаем текст без генерации события textChanged, чтобы не пометить документ как измененный
        self.editor.blockSignals(True)
        self.editor.setPlainText(content)
        self.editor.blockSignals(False)
        self.is_dirty = False
        self.update_status()
        self.status_bar.showMessage(f"Файл загружен: {file_path}")
        self._refresh_window_title()
        
        # Построение дерева из текущего текста
        self.build_tree_from_text(self.editor.toPlainText())
        # Обновляем список недавних
        self._add_recent_file(file_path)

    def open_recent_file(self):
        """Открывает файл из списка недавних, если он существует."""
        action = self.sender()
        if not action:
            return
        file_path = action.data()
        if not file_path:
            return
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Файл не найден", f"Файл отсутствует: {file_path}\nОн будет удален из списка недавних.")
            self._remove_recent_file(file_path)
            return
        if not self.confirm_save_if_dirty():
            return
        self._start_file_loading(file_path)

    def clear_recent_files(self):
        """Очищает список недавних файлов в настройках и меню."""
        self.recent_files = []
        self._save_recent_files()
        self._rebuild_recent_menu()

    def _load_recent_files(self):
        """Загружает список недавних файлов из настроек."""
        # Считываем список путей из настроек
        paths = self.settings.value("recent/files", [], type=list)
        # Гарантируем список строк
        self.recent_files = [p for p in paths if isinstance(p, str)]

    def _save_recent_files(self):
        """Сохраняет текущий список недавних файлов в настройки."""
        self.settings.setValue("recent/files", self.recent_files)

    def _add_recent_file(self, file_path: str):
        """Добавляет путь в начало списка недавних (без дублей, с лимитом)."""
        if not file_path:
            return
        # Удаляем дубликаты и добавляем вперед
        cleaned = [p for p in self.recent_files if p != file_path]
        cleaned.insert(0, file_path)
        # Лимитируем длину
        self.recent_files = cleaned[:10]
        self._save_recent_files()
        self._rebuild_recent_menu()

    def _remove_recent_file(self, file_path: str):
        """Удаляет путь из списка недавних и обновляет меню."""
        self.recent_files = [p for p in self.recent_files if p != file_path]
        self._save_recent_files()
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self):
        """Перестраивает подменю с недавними файлами."""
        if not hasattr(self, 'recent_menu') or self.recent_menu is None:
            return
        self.recent_menu.clear()
        if not self.recent_files:
            empty_action = QAction("(Пусто)", self)
            empty_action.setEnabled(False)
            self.recent_menu.addAction(empty_action)
        else:
            for path in self.recent_files:
                title = os.path.basename(path)
                act = QAction(title, self)
                act.setData(path)
                act.triggered.connect(self.open_recent_file)
                self.recent_menu.addAction(act)
        self.recent_menu.addSeparator()
        clear_action = QAction("Очистить список", self)
        clear_action.triggered.connect(self.clear_recent_files)
        self.recent_menu.addAction(clear_action)

    def on_file_load_error(self, error_msg):
        """Показывает сообщение об ошибке при неудачной загрузке файла."""
        self._progress_bar.setVisible(False)
        self.status_bar.showMessage("Ошибка загрузки файла")
        QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл: {error_msg}")

    def on_file_load_progress(self, progress):
        """Обновляет индикатор прогресса загрузки файла."""
        self._progress_bar.setValue(progress)


    

    def show_about_dialog(self):
        """Показывает профессионально оформленное окно «О программе»."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox, QPushButton
        from PyQt5.QtGui import QFont
        from PyQt5.QtCore import QT_VERSION_STR
        try:
            from PyQt5.QtCore import PYQT_VERSION_STR
        except Exception:
            PYQT_VERSION_STR = ""

        dlg = QDialog(self)
        dlg.setWindowTitle("О программе")

        vbox = QVBoxLayout(dlg)

        # Заголовок с иконкой
        header = QHBoxLayout()
        icon_lbl = QLabel()
        app_icon = self.style().standardIcon(QStyle.SP_FileIcon)
        icon_lbl.setPixmap(app_icon.pixmap(64, 64))
        icon_lbl.setFixedSize(64, 64)
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title = QLabel("Текстовый XML‑редактор")
        f = QFont(title.font())
        f.setPointSize(f.pointSize() + 4)
        f.setBold(True)
        title.setFont(f)
        subtitle = QLabel("Простой и быстрый редактор XML на PyQt5")
        subtitle.setStyleSheet("color: #666;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        vbox.addLayout(header)

        # Описание и ссылка
        desc = QLabel(
            "<p>Редактор с подсветкой синтаксиса, древовидным просмотром, поиском/заменой, печатью и экспортом в HTML/PDF.</p>"
            "<p>Исходный код и инструкции смотрите в README.</p>"
        )
        desc.setWordWrap(True)
        desc.setOpenExternalLinks(True)
        vbox.addWidget(desc)

        # Техническая информация
        import sys as _sys
        info = QLabel(
            f"Версия приложения: 1.0<br>"
            f"Python: {_sys.version.split()[0]} | Qt: {QT_VERSION_STR} | PyQt: {PYQT_VERSION_STR}"
        )
        info.setStyleSheet("color:#555; margin-top:6px;")
        vbox.addWidget(info)

        # Кнопки
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        copy_btn = QPushButton("Копировать информацию")
        btn_box.addButton(copy_btn, QDialogButtonBox.ActionRole)
        vbox.addWidget(btn_box)

        def on_copy():
            details = (
                "Текстовый XML-редактор\n"
                f"Версия: 1.0\n"
                f"Python: {_sys.version}\n"
                f"Qt: {QT_VERSION_STR}\n"
                f"PyQt: {PYQT_VERSION_STR}\n"
            )
            QApplication.clipboard().setText(details)
            self.status_bar.showMessage("Информация скопирована в буфер обмена")

        copy_btn.clicked.connect(on_copy)
        btn_box.accepted.connect(dlg.accept)

        dlg.resize(520, 260)
        dlg.exec_()

    def open_settings_dialog(self):
        """Открывает диалог настроек и применяет выбранные значения."""
        # Считываем текущие значения
        f = self.editor.font()
        pal = self.editor.palette()
        dlg = SettingsDialog(
            self,
            font_family=f.family(),
            font_size=f.pointSizeF(),
            bold=f.bold(),
            italic=f.italic(),
            underline=f.underline(),
            text_color=pal.color(QPalette.Text).name(),
            bg_color=pal.color(QPalette.Base).name(),
            word_wrap=self.editor.wordWrapMode() != QTextOption.NoWrap,
            tag_color=self.settings.value("appearance/tag_color", "#0066cc"),
        )
        if dlg.exec_() == QDialog.Accepted:
            vals = dlg.values()
            # Применяем
            font = self.editor.font()
            font.setFamily(vals["font_family"])
            font.setPointSizeF(vals["font_size"])
            font.setBold(vals["bold"])
            font.setItalic(vals["italic"])
            font.setUnderline(vals["underline"])
            self.editor.setFont(font)

            pal = self.editor.palette()
            pal.setColor(QPalette.Text, QColor(vals["text_color"]))
            pal.setColor(QPalette.Base, QColor(vals["bg_color"]))
            self.editor.setPalette(pal)

            self.toggle_word_wrap(bool(vals["word_wrap"]))

            # Сохраняем
            self.settings.setValue("appearance/font_family", vals["font_family"]) 
            self.settings.setValue("appearance/font_size", vals["font_size"]) 
            self.settings.setValue("appearance/font_bold", vals["bold"]) 
            self.settings.setValue("appearance/font_italic", vals["italic"]) 
            self.settings.setValue("appearance/font_underline", vals["underline"]) 
            self.settings.setValue("appearance/text_color", vals["text_color"]) 
            self.settings.setValue("appearance/bg_color", vals["bg_color"]) 
            self.settings.setValue("appearance/word_wrap", bool(vals["word_wrap"]))
            self.settings.setValue("appearance/tag_color", vals["tag_color"]) 

            # Применить к подсветке
            self.highlighter.set_tag_color(QColor(vals["tag_color"]))

    

    


def main():
    """Точка входа приложения: создаёт и показывает главное окно."""
    app = QApplication(sys.argv)
    app.setApplicationName("Текстовый XML-редактор")
    
    editor = XMLEditor()
    editor.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
