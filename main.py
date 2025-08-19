"""This program will fetch title, source, body, url, timestamp, and keywords from articles, fetching 350 at a time, 3 times daily.
Data is obtained primarily through RSS parsing, and then web scraping with HTML. The data obtained is uploaded
to MongoDB. 
"""

import feedparser # for RSS parsing
from pymongo import MongoClient # for uploading data to MongoDB
import schedule # for scheduling fetches 3 times daily
import pytz # for timezones
import time # to sleep the program when not running
import csv # for parsing the keyword filter set
from parsing import html_scraper # getting the script for the HTML scraper for the PTT stock board
print("importing sentiment_analysis")
from parsing import sentiment_analysis
print("importing deduplication")
from parsing import deduplication
import os
import logging

logging.basicConfig(
    filename = "main.log", 
    level = logging.INFO, 
    format = "%(asctime)s - %(levelname)s - %(message)s"
)

connection_string : str = os.getenv("MONGODB_CONNECTION_STRING")  # replace with wanted connection string
database_name : str = "news_info" # replace with wanted database name
article_collection_name : str = "article_info" # replace with wanted collection name for extracted article info
sentiment_collection_name : str = "sentiment_info" # replace with wanted collection name for sentiment analysis info

# list of urls and source for higher quality websites. The indexes of url and source correspond
high_priority_url_list : list[str] = ["https://news.cnyes.com/rss/v1/news/category/tw_stock", "https://www.moneydj.com/kmdj/RssCenter.aspx?svc=NW&fno=1&arg=X0000000", "https://tw.stock.yahoo.com/rss?category=tw-market", "https://news.cnyes.com/rss/v1/news/category/all"]
high_priority_source_list : list[str] = ["鉅亨網 (Anue)", "MoneyDJ 理財網", "Yahoo 奇摩股市", "鉅亨網 (Anue)"]

# list of urls and source for lower quality websites. The indexes of url and source correspond
lower_priority_url_list : list[str] = ["https://cmsapi.businessweekly.com.tw/?CategoryId=efd99109-9e15-422e-97f0-078b21322450&TemplateId=8E19CF43-50E5-4093-B72D-70A912962D55", "https://techorange.com/feed/", "https://www.inside.com.tw/feed/rss", "https://feeds.feedburner.com/rsscna/finance"]
lower_priority_source_list : list[str] = ["商業週刊", "TechOrange 科技報橘", "Inside (科技媒體)", "中央社財經 (CNA)"]

counter : int = 0 # counts the number of articles fetched

# gets the body text of a given article, using the website title to match it with the proper html search format
def get_body_text(article_link : str, rss_entry, title : str) -> str:
    match title:
        case "Yahoo 奇摩股市" | "商業週刊" | "MoneyDJ 理財網" | "TechOrange 科技報橘":
            text = html_scraper.find_text_by_name(article_link, "article")
            if text is None:
                text = rss_entry.description
                logging.error(f"No body text found for {title} article, RSS desc used. Link: {article_link}")

        case "鉅亨網 (Anue)":
            text = html_scraper.find_text_by_id(article_link, "article-container")
            if text is None:
                text = rss_entry.description
                logging.error(f"No body text found for {title} article, RSS desc used. Link: {article_link}")
        
        case "Inside (科技媒體)":
            text = html_scraper.find_text_by_id(article_link, "article_content")
            if text is None:
                text = rss_entry.description
                logging.error(f"No body text found for {title} article, RSS desc used. Link: {article_link}")

        case "中央社財經 (CNA)":
            text = html_scraper.find_text_by_class(article_link, "centralContent")
            if text is None:
                text = rss_entry.description
                logging.error(f"No body text found for {title} article, RSS desc used. Link: {article_link}")
    
    return text

# fetches articles from one source
def fetch(collection, url : str, title : str, start_index : int) -> None:
    start = time.perf_counter()
    global counter # counts the number of articles fetched
    id = start_index + counter
    NewsFeed = feedparser.parse(url) # parses the RSS of the url
    docs_to_save = [] # holds the documents to be uploaded

    with open("data\keyword_filter_set_zh.csv", mode = "r", encoding = "utf-8", newline = "") as file:

        # loops through each entry in the RSS feed
        for entry in NewsFeed.entries:
            
            article_link = entry.link
            article_title = entry.title
            article_timestamp = entry.published

            # stops fetching data from articles if the 350 limit is reached
            if counter >= 350:
                break

            # parses html for each article's body text case by case depending on the website
            text = get_body_text(article_link, entry, title)

            # skips the article if body text could not be found
            if text is None:
                logging.error(f"No body text found for {title} article, article skipped. Link: {article_link}")
                continue

            article_keywords = []
            
            # loops through the keyword filter set
            file.seek(0)
            csv_reader = csv.reader(file)
            keyword_found = False
            for row in csv_reader:
                if row: # checks if the row isn't empty
                    keyword = row[0]

                    if keyword in article_title or keyword in text:
                        keyword_found = True
                        article_keywords.append(row)
            
            # skips the article if no keywords are found
            if keyword_found == False:
                logging.info(f"No keywords found, article skipped. Link: {article_link}")
                continue
            
            data = {
                "id" : id,
                "title" : article_title,
                "source" : title,
                "body" : text,
                "url" : article_link,
                "timestamp" : article_timestamp,
                "keywords" : article_keywords
            }

            docs_to_save.append(data)
            counter += 1
            id += 1
            print(article_title + " from " + title + " done")

    # stores the articles into the database
    if len(docs_to_save) != 0:
        try:
            collection.insert_many(docs_to_save)
        except Exception as e:
            logging.error(f"Upload to MongoDB failed. Error msg: {e}")
    
    end = time.perf_counter()
    total_time = end - start
    logging.info(f"Time taken to fetch {len(docs_to_save)} from {title}: {total_time}")

# fetches 350 articles
def daily_fetch() -> None:
    start = time.perf_counter()

    global counter
    global connection_string
    global database_name

    # connects to MongoDB
    client = MongoClient(connection_string)
    database = client[database_name]

    # creates a collection w/ the desired name unless it already exists
    try:
        database.create_collection(article_collection_name)
    except Exception as e:
        print(f"Error creating collection: {e}")
    article_collection = database[article_collection_name]

    # finds the index of the next document that will be added (to avoid repetitive parsing of articles from previous fetches)
    start_index = article_collection.count_documents({})
    print(f"start index: {start_index}")

    # fetches articles from high priority websites w/ the 350 article limit
    index : int = 0
    while counter <= 350:
        print("loop iterated")
        # breaks out of the loop if every website has been visited
        if index >= len(high_priority_url_list):
            break
        fetch(article_collection, high_priority_url_list[index], high_priority_source_list[index], start_index)
        index += 1
    
    # fetches articles from lower priority websites w/ the 350 article limit
    index : int = 0
    while counter <= 350:
        if index >= len(lower_priority_url_list):
            break
        fetch(article_collection, lower_priority_url_list[index], lower_priority_source_list[index], start_index)
        index += 1
    
    # fetches the rest of the 350 articles from the PTT stock board
    if counter < 350:
        num = 350 - counter
        html_scraper.PTT_fetch(article_collection, num, start_index + counter)

    # runs deduplication logic using tfidf
    deduplication.tfidf_comparison(article_collection, 1)

    # creates a collection w/ the desired name for the sentiment analysis info, unless one already exists
    try:
        database.create_collection(sentiment_collection_name)
        database.create_collection("entity_match_results")
        database.create_collection("confidence_score_details")
    except Exception as e:
        print(f"Error creating collection: {e}")
    sentiment_collection = database[sentiment_collection_name]
    entity_collection = database["entity_match_results"]
    confidence_collection = database["confidence_score_details"]

    # runs sentiment analysis logic
    #sentiment_analysis.analyze(article_collection, sentiment_collection, entity_collection, confidence_collection, start_index)
    sentiment_analysis.start_async(article_collection, sentiment_collection, entity_collection, confidence_collection, start_index)

    client.close() # closes MongoClient

    end = time.perf_counter()
    logging.info(f"total time taken: {end - start}")

print("fetching")
daily_fetch()
# schedules the daily fetch for the three times each day, in Taiwan's time zone
schedule.every().day.at("07:30", "Asia/Hong_Kong").do(daily_fetch)
schedule.every().day.at("13:30", "Asia/Hong_Kong").do(daily_fetch)
schedule.every().day.at("18:00", "Asia/Hong_Kong").do(daily_fetch)

# pauses the program while waiting for the scheduled fetches
while True:
    schedule.run_pending()
    time.sleep(1)