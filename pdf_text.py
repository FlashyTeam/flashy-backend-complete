import re
from pdfminer.high_level import extract_pages, extract_text

# for page_layout in extract_pages("sample.pdf"):
#     for element in page_layout:
#         print(element)

text = extract_text("pdf.pdf")
print(text)