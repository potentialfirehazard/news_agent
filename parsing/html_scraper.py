"""This program is an HTML web scraper that obtains title, source, body, url, timestamp, and keywords from articles from
the PTT Stock Board. THe data obtained is uploaded to MongoDB. This program is specific to the PTT Stock Board, and cannot
be used for other websites due to different HTML structures. Also contains basic functions for html web scraping to find
text in <p> tags within other tags.
"""

from bs4 import BeautifulSoup # for HTML parsing
import bs4 # for HTML parsing
import requests # to get the HTML of websites
import csv # to parse the keyword filter set
from pymongo import MongoClient # to upload to MongoDB
import logging
import time

logging.basicConfig(
    filename = "html.log", 
    level = logging.INFO, 
    format = "%(asctime)s - %(levelname)s - %(message)s"
)

# gets the BeautifulSoup object of the webpage for scraping
def get_article(url : str) -> BeautifulSoup:
    try:
        response = requests.get(url, timeout = 15)
    except TimeoutError as e:
        logging.error(f"requests timed out. Link of article: {url}")
        return None
    except Exception as e:
        logging.error(f"requests failed for website. Link: {url}. Error msg: {e}")
        return None

    html_content = response.text

    return BeautifulSoup(html_content, "lxml")

def find_text_by_name(article_link : str, name : str) -> str:
    text = ""
    soup = get_article(article_link)
    if soup is None:
        return None
    article = soup.find(name)

    # checks if the correct tag was found
    if article != None:
        paragraphs = article.find_all("p")

        # adds the text in each p tag to the saved text
        for i in paragraphs:
            text += i.get_text()
    
    if text == "":
        logging.error(f"No text found for this article. Link: {article_link}")
        text = None
    
    return text

def find_text_by_id(article_link : str, id_name : str) -> str:
    text = ""
    soup = get_article(article_link)
    if soup is None:
        return None
    article = soup.find(id = id_name)

    # checks if the correct tag was found
    if article != None:
        paragraphs = article.find_all("p")

        # adds the text in each p tag to the saved text
        for i in paragraphs:
            text += i.get_text()
    
    if text == "":
        logging.error(f"No text found for this article. Link: {article_link}")
        text = None

    return text

def find_text_by_class(article_link : str, class_name : str) -> str:
    text = ""
    soup = get_article(article_link)
    if soup is None:
        return None
    article = soup.find(class_ = class_name)

    # checks if the correct tag was found
    if article != None:
        paragraphs = article.find_all("p")

        # adds the text in each p tag to the saved text
        for i in paragraphs:
            text += i.get_text()
    
    if text == "":
        logging.error(f"No text found for this article. Link: {article_link}")
        text = None

    return text

# gets the body text of a PTT Stock Board Post
# WARNING: Specifically customized to PTT Stock Board's html, so if the html structure changes this will stop working
def get_PTT_body_text(soup : BeautifulSoup) -> str:

    article = soup.find_all(class_ = "article-metaline") # uses article-metaline tags as starting point for body text
    if article is None or len(article) == 0:
        logging.error(f"Class 'article-metaline' could not be found in current article. Check if PTT html has been updated.")
        return None
    else:
        tag = article[len(article) - 1] # finds the last article-metaline tag

    text = ""
    while True:
        # breaks from the loop if the end of the page is reached
        if tag is None or tag.next_sibling is None:
            break

        # checks if the next sibling is a tag
        if isinstance(tag, bs4.Tag):

            # checks if the next tag has a class
            if tag.get("class") is not None:

                # ends the loop if the article has ended and the next tag is for comments
                if tag.get("class")[0] == "push":
                    break
        
        # adds the current element to text if it is not a tag object
        else:
            text = text + str(tag)
        
        # sets tag to the next item in the webpage
        tag = tag.next_sibling

    # removing substrings used for formatting on the website for better legibility in the BSON document
    text = text.replace("\n", "")
    text = text.replace("  ", "")
    text = text.replace("===", "")
    text = text.replace("---", "")

    # checks if any text was actually scraped
    if text == "":
        logging.error(f"No text found in current article. Check if PTT html has been updated.")
        text = None

    return(text)

# fetches a specified number of articles from the PTT Stock Board
# WARNING: Specifically customized to PTT Stock Board's html, so if the html structure changes this will stop working
def PTT_fetch(collection, number : int, start_index : int) -> None:
    
    global time
    start = time.perf_counter()
    counter = 0 # counts the number of articles fetched
    url = "https://www.ptt.cc/bbs/stock/index.html"
    cont = True
    index = start_index
    docs_to_save = []

    # opens keyword filter set
    with open("data\keyword_filter_set_zh.csv", mode = "r", encoding = "utf-8", newline = "") as file:

        # loops until the number of articles needed is met
        while cont:

            # finds all articles on the homepage
            content = get_article(url)
            articles = content.find_all(class_ = "title", limit = 350)

            # loops for each article on the page
            for i in articles:

                # finds the tag holding the link and title of each article
                info = i.find("a")
                if info is not None:
                    # parses the article linked
                    article_link = "https://www.ptt.cc" + info.get("href")
                    article = get_article(article_link)
                    
                    # finds where the body text begins
                    for i in article.find_all(class_ = "article-metaline"):
                        if i.find(class_ = "article-meta-tag").get_text() == "時間":
                            timestamp = i.find(class_ = "article-meta-value").get_text()
                    
                    # finds body text
                    text = get_PTT_body_text(article)
                    if text is None:
                        logging.error(f"Body text could not be found for an article from PTT Stock Board. Link: {article_link}")
                        continue

                    article_keywords = []
                    
                    # loops through the keyword filter list
                    file.seek(0)
                    csv_reader = csv.reader(file)
                    for row in csv_reader:
                        if row: # check if the row isn't empty
                            keyword = row[0]
                            if keyword in text or keyword in info.get_text(): # adds the keyword to the list if it is found
                                article_keywords.append(keyword)
                    
                    # skips the article if no keywords are found
                    if len(article_keywords) == 0:
                        logging.info(f"No keywords found for this PTT Stock Board article. Link: {article_link}")
                        continue

                    # creates the file to be stored
                    data = {
                        "id" : index,
                        "title" : info.get_text(),
                        "source" : "PTT Stock Board",
                        "body" : text,
                        "url" : article_link,
                        "timestamp" : timestamp,
                        "keywords" : article_keywords
                    }

                    # saves the file to a list
                    docs_to_save.append(data)
                    counter += 1
                    index += 1
                    
                    # stops fetching if the number of articles needed is reached
                    if counter >= number:
                        cont = False
                        break

            # finds all the buttons for navigating the page
            buttons = get_article(url).find_all(class_ = "btn wide")
            
            if len(buttons) == 0:
                logging.error(f"No buttons found on PTT Stock Board. Check if html has changed.")
                break
            
            # finds the button to go to the next page and sets the link for parsing to the next page
            button_found = False
            for i in buttons:
                    if i.get_text() == "‹ 上頁":
                        url = "https://www.ptt.cc" + i.get("href")
                        button_found = True
            
            if button_found == False:
                logging.error(f"上頁 button not found on PTT Stock Board. Check if html has changed.")
    
    # inserts docs to MongoDB
    try:
        collection.insert_many(docs_to_save)
    except Exception as e:
        logging.error(f"PTT Stock Board docs failed to upload to MongoDB: {e}")
    
    end = time.perf_counter()
    logging.info(f"Time taken to scrape {len(docs_to_save)} articles from PTT Stock Board: {end - start}")

if __name__ == "__main__":
    import os
    from pymongo import MongoClient # for uploading data to MongoDB

    connection_string : str = os.getenv("MONGODB_CONNECTION_STRING")
    database_name : str = "news_info" # replace with wanted database name
    Mongo_client = MongoClient(connection_string)
    database = Mongo_client[database_name]
    try:
        database.create_collection("article_info")
    except Exception as e:
        print(f"Error creating collection: {e}")
    article_collection = database["article_info"]

    PTT_fetch(article_collection, 15, 0)
