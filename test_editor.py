import pytest
import sys
import os

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Editor import XMLEditor


@pytest.fixture(scope="session")
def qapp():
    """Создает QApplication для всех тестов"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def stub_dialogs(monkeypatch):
    """Отключает все диалоги для тестов"""
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    
    # Отключаем диалоги сохранения
    def mock_confirm_save_if_dirty(self):
        return True
    monkeypatch.setattr("Editor.XMLEditor.confirm_save_if_dirty", mock_confirm_save_if_dirty)


@pytest.fixture
def editor(qapp):
    """Создает редактор для каждого теста"""
    editor = XMLEditor()
    yield editor
    editor.close()


def test_editor_creation(editor):
    """Тест: редактор создается без ошибок"""
    assert editor is not None
    assert editor.current_file is None
    # is_dirty может быть True при создании из-за настроек
    assert editor.is_dirty is True


def test_editor_has_components(editor):
    """Тест: у редактора есть все нужные компоненты"""
    assert editor.editor is not None  # текстовое поле
    assert editor.tree is not None    # дерево XML
    assert editor.toolbar is not None  # панель инструментов
    assert editor.status_bar is not None  # статусная строка


def test_text_input(editor):
    """Тест: можно вводить текст в редактор"""
    test_text = "<root>Hello World</root>"
    editor.editor.setPlainText(test_text)
    assert editor.editor.toPlainText() == test_text


def test_text_changed_flag(editor):
    """Тест: флаг изменений работает"""
    # Сбрасываем флаг изменений
    editor.is_dirty = False
    
    # Изменяем текст
    editor.editor.setPlainText("test")
    editor.on_text_changed()
    
    # Теперь файл изменен
    assert editor.is_dirty is True


def test_valid_xml_validation(editor):
    """Тест: валидация корректного XML"""
    valid_xml = "<root><item>test</item></root>"
    editor.editor.setPlainText(valid_xml)
    
    # Валидация должна пройти без ошибок
    editor.validate_xml()


def test_invalid_xml_validation(editor):
    """Тест: валидация некорректного XML"""
    invalid_xml = "<root><unclosed>"
    editor.editor.setPlainText(invalid_xml)
    
    # Валидация должна обработать ошибку
    editor.validate_xml()


def test_pretty_format_xml(editor):
    """Тест: форматирование XML"""
    unformatted = "<root><a>1</a><b>2</b></root>"
    editor.editor.setPlainText(unformatted)
    
    # Форматируем XML
    editor.pretty_format_xml()
    
    # Проверяем, что текст изменился
    formatted = editor.editor.toPlainText()
    assert formatted != unformatted
    assert "<root>" in formatted
    assert "<a>1</a>" in formatted


def test_new_file(editor):
    """Тест: создание нового файла"""
    # Добавляем текст
    editor.editor.setPlainText("some content")
    editor.is_dirty = True
    editor.current_file = "test.xml"
    
    # Создаем новый файл
    editor.new_file()
    
    # Проверяем, что файл очищен
    assert editor.editor.toPlainText() == ""
    assert editor.is_dirty is False
    assert editor.current_file is None


def test_recent_files_add(editor):
    """Тест: добавление файла в недавние"""
    test_file = "/path/to/test.xml"
    
    # Добавляем файл
    editor._add_recent_file(test_file)
    
    # Проверяем, что файл добавлен
    assert test_file in editor.recent_files
    assert editor.recent_files[0] == test_file


def test_recent_files_remove(editor):
    """Тест: удаление файла из недавних"""
    test_file = "/path/to/test.xml"
    editor.recent_files = [test_file, "/path/to/other.xml"]
    
    # Удаляем файл
    editor._remove_recent_file(test_file)
    
    # Проверяем, что файл удален
    assert test_file not in editor.recent_files
    assert len(editor.recent_files) == 1


def test_recent_files_limit(editor):
    """Тест: ограничение количества недавних файлов"""
    # Добавляем много файлов
    for i in range(15):
        editor._add_recent_file(f"/path/to/file{i}.xml")
    
    # Проверяем, что лимит соблюден (максимум 10)
    assert len(editor.recent_files) <= 10


def test_word_wrap_toggle(editor):
    """Тест: переключение переноса строк"""
    from PyQt5.QtGui import QTextOption
    
    # Выключаем перенос
    editor.toggle_word_wrap(False)
    assert editor.editor.wordWrapMode() == QTextOption.NoWrap
    
    # Включаем перенос
    editor.toggle_word_wrap(True)
    assert editor.editor.wordWrapMode() == QTextOption.WordWrap


def test_status_bar_update(editor):
    """Тест: обновление статусной строки"""
    editor.editor.setPlainText("Line 1\nLine 2\nLine 3")
    editor.update_status()
    
    # Проверяем, что статус обновлен
    status = editor.status_bar.currentMessage()
    assert "3" in status  # количество строк
    assert "20" in status  # количество символов (включая переносы строк)


def test_tree_item_creation(editor):
    """Тест: создание элемента дерева"""
    import xml.etree.ElementTree as ET
    
    # Создаем XML элемент
    elem = ET.fromstring("<test attr='value'>text</test>")
    
    # Создаем элемент дерева
    item = editor._make_item_for_element(elem, [0])
    
    # Проверяем, что элемент создан
    assert item is not None
    assert "test" in item.text(0)  # название элемента
    assert item.text(1) == "text"  # текст элемента
    assert "attr=value" in item.text(2)  # атрибуты


def test_empty_tree_build(editor):
    """Тест: построение дерева из пустого текста"""
    editor.build_tree_from_text("")
    
    # Дерево должно быть пустым
    assert editor.tree.topLevelItemCount() == 0


def test_window_title(editor):
    """Тест: заголовок окна"""
    title = editor.windowTitle()
    assert "XML-редактор" in title


if __name__ == "__main__":
    pytest.main([__file__, "-v"])