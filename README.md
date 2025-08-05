# Plaques2Gallery
Wherever I go, I try to explore the local art scene. Along with fairs, music festivals, and theater performances, I always make time to visit at least one art gallery or museum—ideally more.

Since I’ve been traveling quite a lot over the past two years, I’ve encountered hundreds of artworks. Whenever a piece resonates with me, I want to capture that moment. But I quickly realized that photographing the artwork itself wasn’t very helpful - without knowing the title or artist, those photos lacked context. So I started doing something more practical: I took pictures of the museum plaques that are usually displayed next to the artworks.

This solved one problem but created another. Now my photo library is filled with images of plaques from museums around the world—each one informative, but completely detached from the visual memory that triggered my interest in the first place. Without the artwork itself, it’s hard to recall why I found a particular piece compelling.

Manually looking up and downloading each painting would be the most accurate solution, but with hundreds of plaques, that would take far too long. So I built a script to automate the process.

Here’s a quick overview of how it works:
1. Extract the plaque text. The script loops through all the plaque images and uses the functions in ocr_text_extraction.py to extract any readable text. The photos vary in quality, and the plaques follow different formats across museums, so OCR isn’t always perfect.
2. Clean and parse the text. To deal with noisy or inconsistent OCR output, I use Google’s Gemini model to extract a clean, standardized format: “Painting Title by Artist”. This gives me a reliable query to work with. The functions used during this process are available under clean_museum_plaques_text.py
3. Search for the artwork online. Using Google’s Custom Search API, I search for each painting and collect the top 3 URLs that might contain images of the artwork. Due to the API’s daily quota, I split all plaque images into batches of 70 and process one batch per day. This logic is implemented in the main pipeline (.ipynb), which is structured as a Jupyter Notebook to allow easy re-execution of individual blocks with minimal changes.

5. Download the most likely image. With the URLs in hand, I use Playwright to load each page and look for a good candidate image. The main heuristic is simple: select the largest visible image on the page. It’s not perfect, but it works surprisingly well in most cases.
The script also handles cookie banners and prioritizes reliable sources like museum websites or Wikipedia. If none of the three URLs lead to a usable image, the script logs the failure along with the step where the issue occurred. The functions used in this pipeline are also available in web_scrapping.py

Each successfully matched artwork is saved to disk and also recorded in a dictionary that includes:
- the painting name,
- the original museum plaque image associated with it,
- the path to the downloaded image on a local PC
- the museum it came from (if determinable),
- and the source URL of the retrieved image.

Images of the museum plaques can be accessed via this link: https://drive.google.com/file/d/1H1zy3ZTO6ifsAMLCEdFP_aLyJtOTpcia/view?usp=sharing.

All intermediate pipeline results are available at the following link: [some link].

The results for the first batch can be viewed at the following link: [some link].
They have not been filtered to accurately reflect what the pipeline accomplished without human input. Some incorrect matches and missing entries remain. Eventually, I’ll need to manually upload missed paintings and correct mistakes. That said, the pipeline was never meant to produce perfect results — it serves as a preliminary automation step to reduce effort, though some manual refinement is still necessary.

Also, wanted to make a short note that even though I am sharing the code, it was created solely for my personal use - please, do not judge very strictly :)
