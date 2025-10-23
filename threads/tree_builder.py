"""Построение элементов дерева для XML в отдельных потоках.

Содержит два потока:
- TreeBuilderThread: строит корень дерева из XML-текста c отложенной подгрузкой детей
- ElementTreeBuilderThread: строит дерево из готового корневого Element
"""

import xml.etree.ElementTree as ET
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QTreeWidgetItem


def _create_item(elem: ET.Element, path_indices, lazy_children: bool) -> QTreeWidgetItem:
    """Создает ``QTreeWidgetItem`` для элемента.

    При наличии детей добавляет заглушку для последующей
    подгрузки при раскрытии узла.
    """
    value = (elem.text or "").strip()
    attrs = " ".join([f"{k}={v}" for k, v in elem.attrib.items()])
    item = QTreeWidgetItem([elem.tag, value, attrs])
    item.setData(0, Qt.UserRole, path_indices)
    item.setFlags(item.flags() | Qt.ItemIsEditable)

    if lazy_children and len(list(elem)) > 0:
        dummy = QTreeWidgetItem(["Загрузка…", "", ""])  # заглушка
        dummy.setData(0, Qt.UserRole + 1, True)
        item.addChild(dummy)
    return item


def build_subtree(elem: ET.Element, path_indices) -> QTreeWidgetItem:
    """Рекурсивно строит полное поддерево для ``elem``."""
    item = _create_item(elem, path_indices, lazy_children=False)
    for idx, child in enumerate(list(elem)):
        child_item = build_subtree(child, path_indices + [idx])
        item.addChild(child_item)
    return item


class TreeBuilderThread(QThread):
    """Создает корневой элемент дерева по XML-строке (ленивая подгрузка детей)."""
    tree_ready = pyqtSignal(object)  # сигнал с готовым корневым элементом
    error_occurred = pyqtSignal(str)  # сигнал с ошибкой

    def __init__(self, xml_text):
        """Принимает исходный XML-текст для парсинга."""
        super().__init__()
        self.xml_text = xml_text

    def run(self):
        """Парсит XML и эмитит готовый `QTreeWidgetItem` или ошибку."""
        try:
            root = ET.fromstring(self.xml_text)
            root_item = _create_item(root, [], True)
            self.tree_ready.emit(root_item)
        except ET.ParseError as e:
            self.error_occurred.emit(str(e))
        except Exception as e:
            self.error_occurred.emit(f"Неожиданная ошибка: {str(e)}")

class ElementTreeBuilderThread(QThread):
    """Рекурсивно строит дерево из переданного `xml.etree.ElementTree.Element`."""
    tree_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, root_element):
        """Принимает корневой `Element`, из которого строится дерево."""
        super().__init__()
        self.root_element = root_element

    def run(self):
        """Строит `QTreeWidgetItem` и эмитит его либо сообщение об ошибке."""
        try:
            # Строим дерево из корневого элемента
            root_item = build_subtree(self.root_element, [])
            self.tree_ready.emit(root_item)
        except Exception as e:
            self.error_occurred.emit(f"Ошибка построения дерева: {str(e)}")



