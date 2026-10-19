"""Export the reviewed UTF-8 plan as Markdown and a minimal Word document."""
from pathlib import Path
from xml.sax.saxutils import escape
import zipfile
import shutil

root = Path(__file__).resolve().parents[1]
source = root / '织梦_TextileDream_策划案.md'
desktop = Path.home() / 'Desktop'
text = source.read_text(encoding='utf-8')
shutil.copyfile(source, desktop / source.name)
paragraphs = []
for line in text.splitlines():
    heading = line.startswith('#')
    line = line.lstrip('#').strip() if heading else line
    properties = '<w:pPr><w:spacing w:after="180"/></w:pPr>'
    font = '<w:rPr><w:rFonts w:ascii="Calibri" w:eastAsia="Microsoft YaHei"/><w:sz w:val="' + ('30' if heading else '22') + '"/>' + ('<w:b/>' if heading else '') + '</w:rPr>'
    paragraphs.append('<w:p>' + properties + '<w:r>' + font + '<w:t xml:space="preserve">' + escape(line) + '</w:t></w:r></w:p>')
document = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + ''.join(paragraphs) + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr></w:body></w:document>'
target = desktop / '织梦_TextileDream_策划案.docx'
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    archive.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    archive.writestr('word/document.xml', document)
with zipfile.ZipFile(target) as archive:
    from xml.etree import ElementTree
    for name in archive.namelist():
        ElementTree.fromstring(archive.read(name))
print('Desktop Markdown and Word plan exported; XML validated.')
