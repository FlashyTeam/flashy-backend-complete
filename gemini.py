import google.generativeai as genai
import re

load_dotenv()

# Set your Gemini API key
api_key = os.getenv('API_KEY')

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


# Example usage
# text = """
# Photosynthesis is the process by which green plants and some other organisms use sunlight to synthesize foods with the help of chlorophyll. Photosynthesis in plants generally involves the green pigment chlorophyll and generates oxygen as a by-product. The process can be broken down into two stages: the light-dependent reactions and the Calvin cycle. During the light-dependent reactions, energy from light is used to split water molecules, releasing oxygen and transferring energy to ATP and NADPH. In the Calvin cycle, ATP and NADPH are used to convert carbon dioxide into glucose.
# """
# num_flashcards = 5

# generate_flashcards(text, num_flashcards)
