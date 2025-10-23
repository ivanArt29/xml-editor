"""
Модуль для создания и настройки графического интерфейса XML редактора.
Содержит все методы создания UI компонентов, вынесенные из основного класса.
"""

import os
from PyQt5.QtWidgets import (QPlainTextEdit, QVBoxLayout, QWidget, QToolBar, QAction, 
                             QTreeWidget, QTreeWidgetItem, QSplitter, QComboBox, QFontComboBox, 
                             QAbstractItemView, QProgressBar, QStyle, QStatusBar, QMenuBar, QMenu)
from PyQt5.QtGui import QFont, QPalette, QColor, QTextCursor, QIcon, QTextOption
from PyQt5.QtCore import Qt
from ui.syntax_highlighter import XmlHighlighter


class UIBuilder:
    """Класс для создания и настройки UI компонентов XML редактора."""
    
    def __init__(self, main_window):
        """Инициализирует построитель UI с ссылкой на главное окно."""
        self.main_window = main_window
    
    def setup_main_window(self):
        """Настраивает основное окно приложения."""
        self.main_window.setWindowTitle("Текстовый XML-редактор")
        self.main_window.setGeometry(100, 100, 1200, 800)
        self._setup_window_icon()
    
    def _setup_window_icon(self):
        """Устанавливает иконку окна приложения."""
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
        if os.path.exists(icon_path):
            self.main_window.setWindowIcon(QIcon(icon_path))
        else:
            # Fallback на PNG, если ICO не найден
            png_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.png")
            if os.path.exists(png_path):
                self.main_window.setWindowIcon(QIcon(png_path))
            else:
                # Fallback на стандартную иконку
                self.main_window.setWindowIcon(self.main_window.style().standardIcon(QStyle.SP_FileIcon))
    
    def create_central_widget(self):
        """Создает центральный виджет с разделителем и основными компонентами."""
        # Создаем сплиттер с деревом и редактором
        self.main_window.splitter = QSplitter(self.main_window)
        self._create_tree_widget()
        self._create_editor()
        
        # Добавляем виджеты в сплиттер
        self.main_window.splitter.addWidget(self.main_window.tree)
        self.main_window.splitter.addWidget(self.main_window.editor)
        self.main_window.splitter.setStretchFactor(0, 0)
        self.main_window.splitter.setStretchFactor(1, 1)
        # Шире панель дерева по умолчанию
        self.main_window.splitter.setSizes([500, 700])
        
        # Устанавливаем центральный виджет
        self.main_window.setCentralWidget(self.main_window.splitter)
    
    def _create_tree_widget(self):
        """Создает виджет дерева XML."""
        self.main_window.tree = QTreeWidget()
        self.main_window.tree.setHeaderLabels(["Элемент", "Значение", "Атрибуты"])
        # По умолчанию делаем столбец атрибутов шире
        self.main_window.tree.setColumnWidth(2, 300)
        self.main_window.tree.itemClicked.connect(self.main_window.on_tree_item_clicked)
        self.main_window.tree.itemChanged.connect(self.main_window.on_tree_item_changed)
        self.main_window.tree.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed)
        self.main_window.tree.itemExpanded.connect(self.main_window.on_item_expanded)
    
    def _create_editor(self):
        """Создает текстовый редактор с подсветкой синтаксиса."""
        self.main_window.editor = QPlainTextEdit()
        self.main_window.editor.setFont(QFont("Consolas", 12))
        self.main_window.editor.textChanged.connect(self.main_window.on_text_changed)
        self.main_window.editor.cursorPositionChanged.connect(self.main_window.update_status)
        
        # Настройка подсветки синтаксиса
        self.main_window.highlighter = XmlHighlighter(self.main_window.editor.document())
        
        # Настройка переноса строк
        self.main_window.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
    
    def create_toolbars(self):
        """Создает действия для панелей инструментов (без отображения панелей)."""
        self._create_main_toolbar()
        self._create_xml_toolbar()
        self._create_tree_toolbar()
    
    def _create_main_toolbar(self):
        """Создает действия для основной панели инструментов."""
        # Действия для файлов
        self.main_window.new_action = QAction("Новый", self.main_window)
        self.main_window.new_action.setShortcut("Ctrl+N")
        self.main_window.new_action.triggered.connect(self.main_window.new_file)
        
        self.main_window.open_action = QAction("Открыть", self.main_window)
        self.main_window.open_action.setShortcut("Ctrl+O")
        self.main_window.open_action.triggered.connect(self.main_window.open_file)
        
        self.main_window.save_action = QAction("Сохранить", self.main_window)
        self.main_window.save_action.setShortcut("Ctrl+S")
        self.main_window.save_action.triggered.connect(self.main_window.save_file)
        
        self.main_window.save_as_action = QAction("Сохранить как", self.main_window)
        self.main_window.save_as_action.setShortcut("Ctrl+Shift+S")
        self.main_window.save_as_action.triggered.connect(self.main_window.save_as_file)
        
        self.main_window.print_action = QAction("Печать", self.main_window)
        self.main_window.print_action.setShortcut("Ctrl+P")
        self.main_window.print_action.triggered.connect(self.main_window.print_file)

        self.main_window.export_html_action = QAction("Экспорт в HTML", self.main_window)
        self.main_window.export_html_action.triggered.connect(self.main_window.export_to_html)

        self.main_window.export_pdf_action = QAction("Экспорт в PDF", self.main_window)
        self.main_window.export_pdf_action.triggered.connect(self.main_window.export_to_pdf)
    
    def _create_xml_toolbar(self):
        """Создает действия для XML операций."""
        self.main_window.validate_action = QAction("Проверить XML", self.main_window)
        self.main_window.validate_action.setShortcut("F7")
        self.main_window.validate_action.triggered.connect(self.main_window.validate_xml)

        self.main_window.pretty_action = QAction("Форматировать XML", self.main_window)
        self.main_window.pretty_action.setShortcut("Ctrl+Shift+F")
        self.main_window.pretty_action.triggered.connect(self.main_window.pretty_format_xml)

        self.main_window.wrap_action = QAction("Перенос строк", self.main_window)
        self.main_window.wrap_action.setCheckable(True)
        self.main_window.wrap_action.setChecked(False)
        self.main_window.wrap_action.toggled.connect(self.main_window.toggle_word_wrap)
    
    def _create_tree_toolbar(self):
        """Создает действия для управления деревом XML."""
        self.main_window.toggle_tree_action = QAction("Показать/скрыть дерево", self.main_window)
        self.main_window.toggle_tree_action.setCheckable(True)
        self.main_window.toggle_tree_action.setChecked(True)
        self.main_window.toggle_tree_action.toggled.connect(self.main_window.toggle_tree)

        self.main_window.refresh_tree_action = QAction("Обновить дерево", self.main_window)
        self.main_window.refresh_tree_action.setShortcut("F5")
        self.main_window.refresh_tree_action.triggered.connect(self.main_window.build_tree_from_editor)
    
    def create_menus(self):
        """Создает строки меню и их пункты."""
        menubar = self.main_window.menuBar()
        
        # Файл
        self.main_window.file_menu = menubar.addMenu("Файл")
        self.main_window.file_menu.addAction(self.main_window.new_action)
        self.main_window.file_menu.addAction(self.main_window.open_action)
        self.main_window.file_menu.addSeparator()
        self.main_window.file_menu.addAction(self.main_window.save_action)
        self.main_window.file_menu.addAction(self.main_window.save_as_action)

        # Недавние файлы
        self.main_window.recent_menu = self.main_window.file_menu.addMenu("Недавние файлы")
        self.main_window._rebuild_recent_menu()

        self.main_window.file_menu.addSeparator()
        self.main_window.file_menu.addAction(self.main_window.print_action)
        
        # Закрытие
        exit_action = QAction("Закрыть", self.main_window)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.main_window.close)
        self.main_window.file_menu.addSeparator()
        self.main_window.file_menu.addAction(exit_action)

        # Экспорт
        export_menu = menubar.addMenu("Экспорт")
        export_menu.addAction(self.main_window.export_html_action)
        export_menu.addAction(self.main_window.export_pdf_action)

        # Правка
        edit_menu = menubar.addMenu("Правка")
        self.main_window.find_replace_action = QAction("Найти и заменить...", self.main_window)
        self.main_window.find_replace_action.setShortcut("Ctrl+F")
        self.main_window.find_replace_action.triggered.connect(self.main_window.open_find_dialog)
        edit_menu.addAction(self.main_window.find_replace_action)

        # Вид
        view_menu = menubar.addMenu("Вид")
        view_menu.addAction(self.main_window.toggle_tree_action)
        view_menu.addAction(self.main_window.wrap_action)

        # XML
        xml_menu = menubar.addMenu("XML")
        xml_menu.addAction(self.main_window.validate_action)
        xml_menu.addAction(self.main_window.pretty_action)

        # Настройки
        settings_menu = menubar.addMenu("Настройки")
        self.main_window.settings_action = QAction("Настройки", self.main_window)
        self.main_window.settings_action.setShortcut("Ctrl+,")
        self.main_window.settings_action.triggered.connect(self.main_window.open_settings_dialog)
        settings_menu.addAction(self.main_window.settings_action)

        # Справка
        help_menu = menubar.addMenu("Справка")
        about_action = QAction("О программе", self.main_window)
        about_action.triggered.connect(self.main_window.show_about_dialog)
        help_menu.addAction(about_action)
    
    def create_status_bar(self):
        """Создает статусную строку и прогресс-бар."""
        # Создание статусной строки
        self.main_window.status_bar = QStatusBar()
        self.main_window.setStatusBar(self.main_window.status_bar)
        self.main_window.status_bar.showMessage("Готово")
        
        # Создание прогресс-бара для больших файлов
        self.main_window._progress_bar = QProgressBar()
        self.main_window._progress_bar.setVisible(False)
        self.main_window.status_bar.addPermanentWidget(self.main_window._progress_bar)
