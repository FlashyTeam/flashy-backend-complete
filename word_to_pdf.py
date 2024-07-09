import os
from docx import Document
from docx2pdf import convert
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

def docx_to_pdf(docx_path, pdf_path):
    # Convert docx to pdf using docx2pdf
    convert(docx_path, pdf_path)

def main():
    # Path to the input DOCX file
    docx_path = "word.docx"
    
    # Path to the output PDF file
    pdf_path = "output.pdf"

    # Convert the DOCX file to PDF
    docx_to_pdf(docx_path, pdf_path)
    print(f"Converted {docx_path} to {pdf_path}")

if __name__ == "__main__":
    main()
