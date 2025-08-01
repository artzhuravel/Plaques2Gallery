import google.generativeai as genai

def clean_extracted_text(ocr_text, model):
    """
    Extracts the painting title and artist name from raw OCR output using a Gemini language model.

    Parameters
    ----------
    ocr_text : str
        Raw OCR-extracted text from a museum plaque.
    model : genai.GenerativeModel
        An initialized Gemini generative model instance (e.g., `genai.GenerativeModel('gemini-pro')`).

    Returns
    -------
    str
        A cleaned string formatted as "Painting Title by Artist", or just the title/artist
        if the other is missing. No explanation or reasoning is returned.
    """
    system_prompt = (
        'You are a strict data parser. Your task is to extract and return only the *title* and *artist* '
        'from OCR text taken from museum plaques.\n\n'
        'Return the result strictly in this exact format:\n'
        'Painting Title by Artist\n\n'
        'Rules:\n'
        '1. No extra information is allowed — only the title and artist.\n'
        '2. Return only the available information in the specified format if the title or artist is missing or cannot be read. '
        'For example, if the author is missing, do not write "Undefined author" or any placeholder — only return the title in such case.\n'
        '3. If the text contains repetitions (e.g., "Mona Lisa, Da Vinci Mona Lisa, Da Vinci"), return only one clean instance.\n'
        '4. Remove all OCR noise, such as line breaks, symbols, or formatting artifacts.\n'
        '5. Preserve original characters in names (e.g., use German, Italian, French letters if needed). '
        'If OCR has altered special characters (e.g., "é" → "e", "ö" → "o"), restore the original spelling only if it can be determined with certainty from context.\n'
        '6. Do not explain, comment, or reason — return only the final result, exactly as instructed.\n\n'
        'Example:\n'
        'Input:\n'
        'Mona Lisa\nLeonardo da Vinci\nLouvre\n\n'
        'Output:\n'
        'Mona Lisa by Leonardo da Vinci'
    )

    user_prompt = f"{system_prompt}\nOCR text:\n{ocr_text}"
    response = model.generate_content(user_prompt)

    return response.text.strip()