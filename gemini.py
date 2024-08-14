import google.generativeai as genai
import re
import os
from dotenv import load_dotenv
import json
import time

load_dotenv()

# Set your Gemini API key
api_key = os.getenv('API_KEY')

genai.configure(api_key=api_key)

def generate_flashcards(text, num_flashcards):
    prompt = f"Create {num_flashcards} flashcards from the following text:\n\n{text}\n\n Don't write any title \n\n Flashcards:"

    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content(prompt)

    # Extract and print the flashcards in a readable format
    if response and response.candidates:
        flashcards_text = response.candidates[0].content.parts[0].text
        flashcards = flashcards_text.split('\n\n')
        
        for card in flashcards:
            # Remove markdown formatting
            clean_card = re.sub(r'\*\*|\#\#|\n', '', card).strip()
            
            print(clean_card)
            print() # Add an extra newline for better readability
    return response



def generate_quiz(text, num_quiz, retries=3):
    prompt = f"Create {num_quiz} multiple-choice questions with answers from the following text:\n\n{text}\n\nReturn answers in JSON format as an array of objects with 'question', 'options' (an array of four possible answers), and 'answer' keys. Everything should be inline, no backslash n and no backslash either."

    for attempt in range(retries):
        try:
            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content(prompt)
            # print(response)
            
            if response and response.candidates:
                # Extract the text from the response
                quiz_text = response.candidates[0].content.parts[0].text
                
                # Find the start of the JSON array
                json_start = quiz_text.find("[")
                if json_start != -1:
                    json_text = quiz_text[json_start:]
                    try:
                        quiz = json.loads(json_text)
                        return quiz
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error on attempt {attempt + 1}: {e}")
                else:
                    print(f"No JSON array found in the response on attempt {attempt + 1}.")
            else:
                print(f"Error generating flashcards on attempt {attempt + 1}.")
        
        except Exception as e:
            print(f"Unexpected error on attempt {attempt + 1}: {e}")
        
        time.sleep(1)  # Optional: wait 1 second before retrying

    return "Error generating flashcards after multiple attempts."

# Example usage
text = """
Photosynthesis is the process by which green plants and some other organisms use sunlight to synthesize foods with the help of chlorophyll. Photosynthesis in plants generally involves the green pigment chlorophyll and generates oxygen as a by-product. The process can be broken down into two stages: the light-dependent reactions and the Calvin cycle. During the light-dependent reactions, energy from light is used to split water molecules, releasing oxygen and transferring energy to ATP and NADPH. In the Calvin cycle, ATP and NADPH are used to convert carbon dioxide into glucose.
"""
num_flashcards = 5

generate_quiz(text, num_flashcards)
