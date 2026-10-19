import zipfile
from xml.etree import ElementTree as ET
p=r'C:\Users\Huang\Desktop\世界观.docx'
with zipfile.ZipFile(p) as z:
    root=ET.fromstring(z.read('word/document.xml'))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
for para in root.findall('.//w:p', ns):
    text=''.join((node.text or '') for node in para.findall('.//w:t', ns))
    if text.strip(): print(text)
