from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor
from PyQt5.QtCore import QRegExp


class XmlHighlighter(QSyntaxHighlighter):
    """Подсветка синтаксиса XML для QTextDocument."""
    def __init__(self, document):
        """Инициализирует правила подсветки и форматы."""
        super().__init__(document)

        self.rules = []

        # Храним форматы как поля, чтобы менять цвета на лету(подсветку можно изменить без пересоздания хайлайтера и перезагрузки текста)
        self.tag_format = QTextCharFormat()
        self.tag_format.setForeground(QColor(0, 102, 204))  # по умолчанию синий
        self.tag_format.setFontWeight(QFont.Bold)  # Делаем открывающие теги тоже жирными

        attr_name_format = QTextCharFormat()
        attr_name_format.setForeground(QColor(153, 0, 153))  # фиолетовый

        attr_value_format = QTextCharFormat()
        attr_value_format.setForeground(QColor(0, 128, 0))  # зелёный

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(128, 128, 128))  # серый
        comment_format.setFontItalic(True)

        decl_format = QTextCharFormat()
        decl_format.setForeground(QColor(153, 76, 0))  # коричневый
        decl_format.setFontWeight(QFont.Bold)

        entity_format = QTextCharFormat()
        entity_format.setForeground(QColor(204, 0, 0))  # красный

        # Паттерны подсветки (регулярные выражения)
        #Закрывающие теги
        self.rules.append((QRegExp(r"</[^>]+>"), self.tag_format))
        #Открывающие теги 
        self.rules.append((QRegExp(r"<[^!?/][^>]*>"), self.tag_format))
        #Имя атрибута
        self.rules.append((QRegExp(r"\b[\w:-]+\b(?=\=)"), attr_name_format))
        #Значение атрибута в кавычках
        self.rules.append((QRegExp(r'(["\']).*?\1'), attr_value_format))
        #Комментарии
        self.rules.append((QRegExp(r"<!--[^>]*-->"), comment_format))
        #Декларация XML
        self.rules.append((QRegExp(r"<\?xml[^>]*\?>"), decl_format))
        #DOCTYPE
        self.rules.append((QRegExp(r"<!DOCTYPE[^>]*>"), decl_format))
        #Сущности
        self.rules.append((QRegExp(r"&[a-zA-Z0-9#]+;"), entity_format))

    def highlightBlock(self, text):
        """Выделяет найденные паттерны в одном текстовом блоке."""
        for pattern, fmt in self.rules:
            index = pattern.indexIn(text, 0)
            while index >= 0:
                length = pattern.matchedLength()
                if length == 0:
                    break
                self.setFormat(index, length, fmt)
                index = pattern.indexIn(text, index + length)

    def set_tag_color(self, color: QColor):
        """Меняет цвет подсветки тегов и перерисовывает документ."""
        self.tag_format.setForeground(color)
        self.rehighlight()
