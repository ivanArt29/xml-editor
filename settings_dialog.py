from PyQt5.QtWidgets import QDialog, QFormLayout, QFontComboBox, QComboBox, QCheckBox, QPushButton, QWidget, QDialogButtonBox
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import QColorDialog


class SettingsDialog(QDialog):
    """Диалог настроек внешнего вида редактора и подсветки."""

    def __init__(self, parent=None, *, font_family, font_size, bold, italic, underline, text_color, bg_color, word_wrap, tag_color):
        """Создает форму с параметрами шрифта, цветов, переноса и цвета тегов."""
        super().__init__(parent)
        self.setWindowTitle("Настройки")

        self._text_color = QColor(text_color)
        self._bg_color = QColor(bg_color)
        self._tag_color = QColor(tag_color)

        form = QFormLayout(self)

        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(font_family))
        form.addRow("Шрифт", self.font_combo)

        self.size_combo = QComboBox()
        self.size_combo.setEditable(True)
        self.size_combo.addItems(["8", "9", "10", "11", "12", "14", "16", "18", "20", "22", "24", "26", "28", "36", "48", "72"])
        self.size_combo.setCurrentText(str(int(font_size)))
        form.addRow("Размер", self.size_combo)

        self.bold_cb = QCheckBox("Жирный")
        self.bold_cb.setChecked(bool(bold))
        self.italic_cb = QCheckBox("Курсив")
        self.italic_cb.setChecked(bool(italic))
        self.underline_cb = QCheckBox("Подчеркивание")
        self.underline_cb.setChecked(bool(underline))
        from PyQt5.QtWidgets import QHBoxLayout
        styles_row = QHBoxLayout()
        styles_row.addWidget(self.bold_cb)
        styles_row.addWidget(self.italic_cb)
        styles_row.addWidget(self.underline_cb)
        form.addRow("Стиль", QWidget())
        form.itemAt(form.rowCount()-1, QFormLayout.FieldRole).widget().setLayout(styles_row)

        # Цвета
        self.text_color_btn = QPushButton("Выбрать…")
        self.text_color_btn.clicked.connect(self._pick_text_color)
        self._update_button_color(self.text_color_btn, self._text_color)
        form.addRow("Цвет текста", self.text_color_btn)

        self.bg_color_btn = QPushButton("Выбрать…")
        self.bg_color_btn.clicked.connect(self._pick_bg_color)
        self._update_button_color(self.bg_color_btn, self._bg_color)
        form.addRow("Цвет фона", self.bg_color_btn)

        self.wrap_cb = QCheckBox("Перенос строк")
        self.wrap_cb.setChecked(bool(word_wrap))
        form.addRow("Перенос", self.wrap_cb)

        # Цвет тегов
        self.tag_color_btn = QPushButton("Выбрать…")
        self.tag_color_btn.clicked.connect(self._pick_tag_color)
        self._update_button_color(self.tag_color_btn, self._tag_color)
        form.addRow("Цвет тегов", self.tag_color_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _update_button_color(self, btn: QPushButton, color: QColor):
        """Обновляет фон кнопки под выбранный цвет для наглядности."""
        btn.setStyleSheet(f"background-color: {color.name()};")

    def _pick_text_color(self):
        """Открывает палитру и сохраняет выбранный цвет текста."""
        color = QColorDialog.getColor(self._text_color, self, "Выберите цвет текста")
        if color.isValid():
            self._text_color = color
            self._update_button_color(self.text_color_btn, color)

    def _pick_bg_color(self):
        """Открывает палитру и сохраняет выбранный цвет фона редактора."""
        color = QColorDialog.getColor(self._bg_color, self, "Выберите цвет фона")
        if color.isValid():
            self._bg_color = color
            self._update_button_color(self.bg_color_btn, color)

    def _pick_tag_color(self):
        """Открывает палитру и сохраняет цвет подсветки тегов."""
        color = QColorDialog.getColor(self._tag_color, self, "Выберите цвет тегов")
        if color.isValid():
            self._tag_color = color
            self._update_button_color(self.tag_color_btn, color)

    
    def values(self):
        """Возвращает текущие выбранные значения настроек диалога."""
        return {
            "font_family": self.font_combo.currentFont().family(),
            "font_size": float(self.size_combo.currentText()),
            "bold": self.bold_cb.isChecked(),
            "italic": self.italic_cb.isChecked(),
            "underline": self.underline_cb.isChecked(),
            "text_color": self._text_color.name(),
            "bg_color": self._bg_color.name(),
            "word_wrap": self.wrap_cb.isChecked(),
            "tag_color": self._tag_color.name(),
        }


