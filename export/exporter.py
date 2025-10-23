from typing import Optional
from PyQt5.QtGui import QPalette
from PyQt5.QtPrintSupport import QPrinter


def _qcolor_to_css(c) -> str:
    return f"#{c.red():02x}{c.green():02x}{c.blue():02x}"


def export_to_html(text: str, font, palette: QPalette, target_path: str) -> None:
    text_color = palette.color(QPalette.Text)
    bg_color = palette.color(QPalette.Base)

    style = (
        f"body {{ background: {_qcolor_to_css(bg_color)}; color: {_qcolor_to_css(text_color)}; "
        f"font-family: '{font.family()}'; font-size: {font.pointSize()}pt; "
        f"font-weight: {'bold' if font.bold() else 'normal'}; "
        f"font-style: {'italic' if font.italic() else 'normal'}; "
        f"text-decoration: {'underline' if font.underline() else 'none'}; }}"
    )

    import html as _html
    html_text = _html.escape(text).replace('\n', '<br>')
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>" +
        style +
        "</style></head><body>" + html_text + "</body></html>"
    )

    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(html)


def export_to_pdf(document, target_path: str) -> None:
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(target_path)
    document.print(printer)
