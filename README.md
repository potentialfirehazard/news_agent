## Description

News Agent will scrape 350 articles at 3 scheduled times a day (07:30, 13:30, 18:00  UTC+8) from a list of sources. The sources are split into high priority and low priority categories, and the high priority list is fetched first. The low priority list will be fetched after, and the rest of the articles needed to meet the 350 quota will be scraped from PTT Stock Board. The articles are checked for keywords and skipped if no keywords are found, and they are also checked against the articles already in the database to see if there is already a duplicate in the database. If a duplicate is found, the article is skipped. Information from these articles are stored in the "article_info" collection in the database. After parsing, the articles go through deduplication through TF-IDF or SBERT vectorization and cosine similarity. Most exact duplicates should have already been skipped, so this step would be for removing articles on similar topics. There is a threshold parameter to control what similarity score is considered too high, which allows for customization of how similar articles must be for removal. After deduplication, the articles go through sentiment analysis via concurrent calls to OpenAI. This creates three documents for each article: one for general sentiment analysis, one for detail on the confidence score given, and one for entity matches. These are each stored in a separate collection, and each parsed article is linked to its three connecting analysis files by the "id" field in each document.    
Python Version 3.11.9

## Components

main.py handles the scheduling of runs and all RSS parsing, as well as calling functions from other modules.  
Parsing folder contains the following modules:  
- html_scraper.py: handles all html parsing using BeautifulSoup  
- deduplication.py: handles deduplication via tf-idf or sbert vectorization and cosine similarity.  
- sentiment_analysis.py: gets responses from OpenAI to analyze the news scraped from main.py

## Configurables:

- deduplication.py— tfidf_comparison /sbert_comparison— either can be utilized
- deduplication.py — tfidf_comparison/sbert_comparison—threshold parameter can be changed when the function is called depending on what similarity score is considered “too similar”
- html_scraper.py—find_text_by_name/find_text_by_id/find_text_by_class—can all be utilized to find the body text in p tags within the tag identified by name, id, or class.
- main.py—connection_string—replace with the connection string of the desired MongoDB database
- main.py—database_name—replace with the name of the desired database
- sentiment_analysis.py—async_analyze—will require OpenAI key, currently is using a key saved to my environment

## Setup:

```bash
     # Create virtual environment
     python -m venv venv

     # Activate (Mac/Linux)
     source venv/bin/activate

     # Activate (Windows)
     venv\Scripts\activate

     # Install dependencies
     pip install -r requirements.txt
```
-MongoDB connection string and database name must be updated to that of your account/database in main.py  
-OpenAI API key is also needed

## Testing:

- **main.py** — To test: run the daily_fetch() function, errors/time taken for each step are logged. — Expected result: fetches information from 350 articles each run, 3 runs scheduled per day—Note: the functions in main.py rely on other modules (deduplication.py, sentiment_analysis.py, html_scraper.py)
- **html_scraper.py**—To test: run the file (has logic to run on its own)—Expected result: PTT scraping functions gather information from a specific amount of articles and stores in MongoDB. Functions to get body text can be tested with the fetch() function in main.py.
- **deduplication.py**—To test: run the file (has logic to run on its own)— Expected result: Removes duplicates from a MongoDB collection. Titles of deleted articles are logged and can be used to determine if the deduplication logic is running properly.
- **sentiment_analysis.py**—To test: run the file (has logic to run on its own)—Expected result: gets OpenAI responses to analyze all documents from the specified start index, stores 3 types of results (entity match, sentiment analysis, confidence score detail) in 3 different collections.
