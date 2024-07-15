from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from flask_cors import CORS
from docx import Document
from pptx import Presentation
import fitz  # PyMuPDF
import os
import re
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Set your Gemini API key
api_key = os.getenv('API_KEY')
genai.configure(api_key=api_key)

app = Flask(__name__)
CORS(app)  # Enable CORS
app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

ALLOWED_EXTENSIONS = {'pdf', 'pptx', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        file_type = file.filename.rsplit('.', 1)[1].lower()
        try:
            flashcards = ''
            if file_type == 'pdf':
                flashcards = extract_text_from_pdf(file_path)
            elif file_type == 'pptx':
                flashcards = extract_text_from_pptx(file_path)
            elif file_type == 'docx':
                flashcards = extract_text_from_docx(file_path)
            else:
                flashcards = 'Unsupported file type'
            os.remove(file_path)
            return jsonify({'type': file_type, 'flashcards': flashcards})
        except Exception as e:
            print(f"Error processing file: {e}")
            return jsonify({'error': str(e)})
    return jsonify({'error': 'File type not allowed'})

def extract_text_from_docx(docx_path):
    try:
        doc = Document(docx_path)
        text = []
        for para in doc.paragraphs:
            text.append(para.text)
        extracted_text = '\n'.join(text)
        flashcards = generate_flashcards(extracted_text, 8)
        print(f"Extracted text from DOCX: {extracted_text}")
        print(f"Generated flashcards: {flashcards}")
        return flashcards
    except Exception as e:
        return f"Error extracting text from DOCX: {str(e)}"

def extract_text_from_pptx(pptx_path):
    try:
        prs = Presentation(pptx_path)
        text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text.append(shape.text)
        extracted_text = '\n'.join(text)
        flashcards = generate_flashcards(extracted_text, 8)
        print(f"Extracted text from PPTX: {extracted_text}")
        print(f"Generated flashcards: {flashcards}")
        return flashcards
    except Exception as e:
        return f"Error extracting text from PPTX: {str(e)}"

def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text.append(page.get_text())
        extracted_text = '\n'.join(text)
        flashcards = generate_flashcards(extracted_text, 8)
        print(f"Extracted text from PDF: {extracted_text}")
        print(f"Generated flashcards: {flashcards}")
        return flashcards
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"

def generate_flashcards(text, num_flashcards):
    prompt = f"Create {num_flashcards} flashcards from the following text:\n\n{text}\n\n Don't write any title \n\n Flashcards:"

    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content(prompt)

    # Extract and print the flashcards in a readable format
    if response and response.candidates:
        flashcards_text = response.candidates[0].content.parts[0].text
        flashcards = flashcards_text.split('\n\n')
        
        clean_flashcards = []
        for card in flashcards:
            # Remove markdown formatting
            clean_card = re.sub(r'\*\*|\#\#|\n', '', card).strip()
            clean_flashcards.append(clean_card)
        
        return clean_flashcards
    return "Error generating flashcards"

if __name__ == '__main__':
    app.run(debug=True)
