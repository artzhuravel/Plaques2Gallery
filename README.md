# Plaques2Gallery
Wherever I go, I try to explore the local art scene. Along with fairs, music festivals, and theater performances, I always make time to visit at least one art gallery or museum—ideally more.

Since I’ve been traveling quite a lot over the past two years, I’ve encountered hundreds of artworks. Whenever a piece resonates with me, I want to capture that moment. But I quickly realized that photographing the artwork itself wasn’t very helpful - without knowing the title or artist, those photos lacked context. So I started doing something more practical: I took pictures of the museum plaques that are usually displayed next to the artworks.

This solved one problem but created another. Now my photo library is filled with images of plaques from museums around the world—each one informative, but completely detached from the visual memory that triggered my interest in the first place. Without the artwork itself, it’s hard to recall why I found a particular piece compelling.

Manually looking up and downloading each painting would be the most accurate solution, but with hundreds of plaques, that would take far too long. So I built a script to automate the process.

Here’s a quick overview of how it works:
1. Extract the plaque text. The script loops through all the plaque images and uses the functions in ocr_text_extraction.py to extract any readable text. The photos vary in quality, and the plaques follow different formats across museums, so OCR isn’t always perfect.
2. Clean and parse the text. To deal with noisy or inconsistent OCR output, I use Google’s Gemini model to extract a clean, standardized format: “Painting Title by Artist”. This gives me a reliable query to work with. The functions used during this process are available under clean_museum_plaques_text.py
3. Search for the artwork online. Using Google’s Custom Search API, I search for each painting and collect the top 3 URLs that might contain images of the artwork. Since I’m limited by the API’s daily quota, I divide all plaque images into batches of 70 and process one batch per day. This was included in the main pipeline (.ipynb file).
4. Download the most likely image. With the URLs in hand, I use Playwright to load each page and look for a good candidate image. The main heuristic is simple: select the largest visible image on the page. It’s not perfect, but it works surprisingly well in most cases.
The script also handles cookie banners and prioritizes reliable sources like museum websites or Wikipedia. If none of the three URLs lead to a usable image, the script logs the failure along with the step where the issue occurred. The functions used in this pipeline are also available in web_scrapping.py

Each successfully matched artwork is saved to disk and also recorded in a dictionary that includes:
- the painting name,
- the original museum plaque image associated with it,
- the path to the downloaded image on a local PC
- the museum it came from (if determinable),
- and the source URL of the retrieved image.

Even though I am sharing the code, it was created solely for my personal use - please, do not judge very strictly :)
