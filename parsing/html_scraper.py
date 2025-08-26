"""This program is an HTML web scraper that obtains title, source, body, url, timestamp, and keywords from articles from
the PTT Stock Board. THe data obtained is uploaded to MongoDB. This program is specific to the PTT Stock Board, and cannot
be used for other websites due to different HTML structures. Also contains basic functions for html web scraping to find
text in <p> tags within other tags. Also contains a scraper for cmoney, but it has not been thoroughly tested yet so it is not
currently implemented in main.
"""

from bs4 import BeautifulSoup # for HTML parsing
import bs4 # for HTML parsing
import requests # to get the HTML of websites
import logging
import time
import os
import pytz
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from newspaper import Article
from langdetect import detect
import math

logging.basicConfig(
    filename = "html.log", 
    encoding = "utf-8", 
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

# finds text in <p> tags under the tag with a certain name
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

# finds the text in <p> tags under a tag with a certain id
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

# finds the text in <p> tags under a tag with a certain class
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
def PTT_fetch(collection, number : int, start_index : int, keywords : set) -> None:
    
    global time
    start = time.perf_counter()
    counter = 0 # counts the number of articles fetched
    url = "https://www.ptt.cc/bbs/stock/index.html"
    cont = True
    index = start_index
    docs_to_save = []

    # loops until the number of articles needed is met
    while cont:

        # finds all articles on the homepage
        tries = 0
        while tries < 3:
            content = get_article(url)
            articles = content.find_all(class_ = "title", limit = number)
            if articles is None:
                tries += 1
                continue
            else:
                break
        if tries == 3:
            logging.error("Requests timed out")
            return None


        # loops for each article on the page
        for i in articles:

            # finds the tag holding the link and title of each article
            info = i.find("a")
            if info is not None:
                # parses the article linked
                article_link = "https://www.ptt.cc" + info.get("href")
                article = get_article(article_link)
                title = info.get_text()

                # finds the timestamp
                skip_article = False
                try:
                    for i in article.find_all(class_ = "article-metaline"):
                        if i.find(class_ = "article-meta-tag").get_text() == "時間":
                            timestamp_string = i.find(class_ = "article-meta-value").get_text()
                            format = f"%a %b %d %H:%M:%S %Y"
                            try:
                                datetime_object = datetime.strptime(timestamp_string, format)
                            except Exception as e:
                                logging.error(f"Error converting {title} article to datetime object: {e}")
                                skip_article = True
                                break
        
                            # changes the datetime object to UTC+8 timezone (uses localize b/c PTT does not include time zone)
                            tw_timezone = pytz.timezone("Etc/GMT-8")
                            converted_dt = tw_timezone.localize(datetime_object)
                except Exception as e:
                    logging.error(f"Could not find timestamp for PTT post: {e}")
                    continue
                
                if skip_article:
                    continue

                # finds body text
                text = get_PTT_body_text(article)
                if text is None:
                    logging.error(f"Body text could not be found for an article from PTT Stock Board. Link: {article_link}")
                    continue

                article_keywords = []
                
                # loops through the keyword filter set
                keyword_found = False
                for keyword in keywords:
                    if keyword in title or keyword in text:
                        keyword_found = True
                        article_keywords.append(keyword)
                
                # skips the article if no keywords are found
                if keyword_found == False:
                    logging.info(f"No keywords found for this PTT Stock Board article. Link: {article_link}")
                    continue

                # creates the file to be stored
                data = {
                    "id" : index,
                    "title" : title,
                    "source" : "PTT Stock Board",
                    "body" : text,
                    "url" : article_link,
                    "timestamp" : converted_dt,
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

# scrapes a set amount of articles from cmoney w/ Selenium
def cmoney_scraper(collection, number : int, start_index : int, keywords : set):
    global time
    start = time.perf_counter()
    counter = 0 # counts the number of articles fetched
    url = "https://www.cmoney.tw/forum/popular/buzz?tab=news"
    cont = True
    index = start_index
    docs_to_save = []
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")

    driver = webdriver.Chrome(options) 
    driver.get(url)
    time.sleep(5) # allows page to load

    # get rid of popup if it is detected
    print("finding popup")
    try:
        popup_container = driver.find_element(By.ID, "qgraphFakePromptContainer")
        button = popup_container.find_element(By.CLASS_NAME, "aiq-MLWa4b")
        button.click()
    except:
        logging.info("no popup detected.")
    
    # loads as many articles as needed by scrolling to the end of the page
    num_loads = math.ceil(number / 10) + 2 # adds 2 scrolls for a buffer if articles are skipped
    print(num_loads)
    for i in range(num_loads):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    # loops until the number of articles needed is met
    while cont:
        
        # finds each article container
        soup = BeautifulSoup(driver.page_source, "lxml")
        container = soup.find(class_ = "page__list")
        articles = container.find_all("section")

        # loops through every article on the page
        for article in articles:
            # makes sure the "article" is actually an article and not an ad or something else
            element_classes = article["class"]
            if element_classes[0] != "page__section":
                continue
            
            # finds the source and cleans the text
            source_container_tag = article.find(class_ = "articleContentOfficial__headLine")
            a_tag = source_container_tag.find("a")
            source_tag = a_tag.find("div")
            source = source_tag.get_text()
            source = source.strip()

            # finds the link
            link_tag = article.find("a")
            article_link = link_tag.get("href")

            # finds the title and cleans the text
            title_tag = article.find("h3")
            title = title_tag.get_text()
            title = title.strip()
            
            # detects the language
            detected_language = detect(title)
            # defaults to chinese if detected language is not en, b/c langdetect kept detecting korean/vietnamese instead
            if detected_language != "en":
                detected_language = "zh"

            # creates an article object for the article
            expanded_article = Article(article_link, language = detected_language)
            try:
                expanded_article.download()
                expanded_article.parse()
            except Exception as e:
                print(f"download failed for link: {article_link}. Message: {e}")
                logging.error(f"download failed for link: {article_link}. Message: {e}")
                continue
            
            # gets the body text of the article
            text = expanded_article.text
            
            # loops through the keyword filter set
            article_keywords = []
            keyword_found = False
            for keyword in keywords:
                if keyword in title or keyword in text:
                    keyword_found = True
                    article_keywords.append(keyword)

            # skips the article if no keywords are found
            if keyword_found == False:
                logging.info(f"No keywords found for this 股市同學會 post. Title: {title}")
                continue
            
            # gets the timestamp of the article
            timestamp = expanded_article.publish_date
        
            # creates the file to be stored
            data = {
                "id" : index,
                "title" : title,
                "source" : source,
                "body" : text,
                "url" : article_link,
                "timestamp" : timestamp,
                "keywords" : article_keywords
            }

            # saves the file to a list
            docs_to_save.append(data)
            counter += 1
            index += 1
            print(f"{title} done")
            # stops fetching if the number of articles needed is reached
            if counter >= number:
                cont = False
                break

    # inserts docs to MongoDB
    try:
        collection.insert_many(docs_to_save)
    except Exception as e:
        logging.error(f"股市同學會 docs failed to upload to MongoDB: {e}")
    
    end = time.perf_counter()
    logging.info(f"Time taken to scrape {len(docs_to_save)} articles from 股市同學會: {end - start}")

if __name__ == "__main__":
    import os
    from pymongo import MongoClient # for uploading data to MongoDB
    import csv # to parse the keyword filter set

    connection_string : str = os.getenv("MONGODB_CONNECTION_STRING")
    database_name : str = "news_info" # replace with wanted database name
    Mongo_client = MongoClient(connection_string)
    database = Mongo_client[database_name]
    try:
        database.create_collection("article_info")
    except Exception as e:
        print(f"Error creating collection: {e}")
    article_collection = database["article_info"]

    # creates a set of keywords
    keywords = set()
    keyword_file_path = os.path.join("data", "keyword_filter_set_zh.csv")
    with open(keyword_file_path, mode = "r", encoding = "utf-8", newline = "") as file:
        reader = csv.DictReader(file)
        for row in reader:
            keywords.add(row["Keyword"])
    
    # creates a set of stock names
    stock_names = set()
    stock_file_path = os.path.join("data", "TW_stock_list.csv")
    with open(stock_file_path, mode = "r", encoding = "utf-8", newline = "") as file:
        reader = csv.DictReader(file)
        for row in reader:
            stock_names.add(row["Cleaned company names"])
    
    # adds stock names to the list of keywords searched
    keywords.update(stock_names)

    cmoney_scraper(article_collection, 31, 0, keywords)
    PTT_fetch(article_collection, 15, 31, keywords)