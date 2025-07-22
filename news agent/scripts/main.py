'''This program will fetch title, source, body, url, timestamp, and keywords from articles, fetching 350 at a time, 3 times daily.
Data is obtained primarily through RSS parsing, and then web scraping with HTML. The data obtained is uploaded
to MongoDB.'''

import feedparser # for RSS parsing
from pymongo import MongoClient # for uploading data to MongoDB
import schedule # for scheduling fetches 3 times daily
import time # to sleep the program when not running
import csv # for parsing the keyword filter set
import PTT_scraper # getting the script for the HTML scraper for the PTT stock board
from newspaper import Article # for parsing the body text of articles
from newspaper import Config # for configuring the Article object
from newspaper import ArticleException # for handling exceptions in the Article object
from bs4 import BeautifulSoup # for HTML parsing
import requests # to get the HTML of websites
import deduplication # getting method for deduplication

connection_string = "mongodb+srv://madelynsk7:vy97caShIMZ2otO6@testcluster.aosckrl.mongodb.net/" # replace with wanted connection string
database_name = "news_info" # replace with wanted database name

# list of urls and source for higher quality websites, indexes of url and source correspond
high_priority_url_list = ["https://news.cnyes.com/rss/v1/news/category/tw_stock", "https://www.moneydj.com/kmdj/RssCenter.aspx?svc=NW&fno=1&arg=X0000000", "https://tw.stock.yahoo.com/rss?category=tw-market", "https://news.cnyes.com/rss/v1/news/category/all", "https://news.cnyes.com/rss/v1/news/category/headline"]
high_priority_source_list = ["鉅亨網 (Anue)", "MoneyDJ 理財網", "Yahoo 奇摩股市", "鉅亨網 (Anue)", "鉅亨網 (Anue)"]

# list of urls and source for lower quality websites, indexes of url and source correspond
lower_priority_url_list = ["https://cmsapi.businessweekly.com.tw/?CategoryId=efd99109-9e15-422e-97f0-078b21322450&TemplateId=8E19CF43-50E5-4093-B72D-70A912962D55", "https://techorange.com/feed/", "https://www.inside.com.tw/feed/rss", "https://feeds.feedburner.com/rsscna/finance"]
lower_priority_source_list = ["商業週刊", "TechOrange 科技報橘", "Inside (科技媒體)", "中央社財經 (CNA)"]

counter = 0 # counts the number of articles fetched

# fetches articles from one source
def fetch(url, title):
    global connection_string
    global database_name

    # connects to the MongoDB database
    client = MongoClient(connection_string)
    database = client[database_name]

    NewsFeed = feedparser.parse(url) # parses the RSS of the url

    # opens the keyword filter file
    with open("news agent\data\keyword_filter_set_zh.csv", mode = "r", encoding = "utf-8", newline = "") as file:

        # loops through each entry in the RSS feed
        for i in range(len(NewsFeed.entries)):
            global counter

            article_link = NewsFeed.entries[i].link
            article_title = NewsFeed.entries[i].title
            article_timestamp = NewsFeed.entries[i].published

            # stops fetching data from articles if the 350 limit is reached
            if counter >= 350:
                break

            text = ""

            # parses html for each article's body text case by case depending on the website
            match title:
                case "Yahoo 奇摩股市" | "商業週刊" | "MoneyDJ 理財網" | "TechOrange 科技報橘":
                    # skips the article if an error occurs (infrequent, should not impact the number of articles retrieved)
                    try:
                        response = requests.get(article_link)
                    except:
                        continue
                    
                    # creates a BeautifulSoup object from the article
                    html_content = response.text
                    soup = BeautifulSoup(html_content, "lxml")

                    # finds the tag containing the article
                    article = soup.find("article")
                    # checks if the correct tag was found
                    if article != None:
                        paragraphs = article.find_all("p")

                        # adds the text in each p tag to the saved text
                        for i in paragraphs:
                            text += i.get_text()
                    # makes the text the RSS description if the article cannot be parsed       
                    else:
                        text = NewsFeed.entries[i].description

                case "鉅亨網 (Anue)":
                    # skips the article if an error occurs (infrequent, should not impact the number of articles retrieved)
                    try:
                        response = requests.get(article_link)
                    except:
                        continue

                    # creates a BeautifulSoup object from the article
                    html_content = response.text
                    soup = BeautifulSoup(html_content, "lxml")

                    # finds the tag containing the article
                    article = soup.find(id = "article-container")
                    # checks if the correct tag was found
                    if article != None:
                        paragraphs = article.find_all("p")

                        # adds the text in each p tag to the saved text
                        for i in paragraphs:
                            text += i.get_text() 
                    # makes the text the RSS description if the article cannot be parsed         
                    else:
                        text = NewsFeed.entries[i].description
                
                case "Inside (科技媒體)":
                    # skips the article if an error occurs (infrequent, should not impact the number of articles retrieved)
                    try:
                        response = requests.get(article_link)
                    except:
                        continue

                    # creates a BeautifulSoup object from the article
                    html_content = response.text
                    soup = BeautifulSoup(html_content, "lxml")

                    # finds the tag containing the article
                    article = soup.find(id = "article_content")
                    # checks if the correct tag was found
                    if article != None:
                        paragraphs = article.find_all("p")

                        # adds the text in each p tag to the saved text
                        for i in paragraphs:
                            text += i.get_text()    
                    # makes the text the RSS description if the article cannot be parsed      
                    else:
                        text = NewsFeed.entries[i].description

                case "中央社財經 (CNA)":
                    # skips the article if an error occurs (infrequent, should not impact the number of articles retrieved)
                    try:
                        response = requests.get(article_link)
                    except:
                        continue

                    # creates a BeautifulSoup object from the article
                    html_content = response.text
                    soup = BeautifulSoup(html_content, "lxml")

                    # finds the tag containing the article
                    article = soup.find(class_ = "centralContent")
                    # checks if the correct tag was found
                    if article != None:
                        paragraphs = article.find_all("p")

                        # adds the text in each p tag to the saved text
                        for i in paragraphs:
                            text += i.get_text()    
                    # makes the text the RSS description if the article cannot be parsed      
                    else:
                        text = NewsFeed.entries[i].description


            article_keywords = [] # list to hold the keywords found in the article
            
            # loops through the keyword filter set
            file.seek(0)
            csv_reader = csv.reader(file)
            keyword_found = False
            for row in csv_reader:
                if row: #check if the row isn't empty
                    keyword = row[0]

                    # continues adding the article if a keyword is found
                    if keyword in article_title or keyword in text:
                        keyword_found = True
                        article_keywords.append(row)
            
            # skips the article if no keywords are found
            if keyword_found == False:
                continue

            # creates the file to be stored
            data = {
                "title" : article_title,
                "source" : title,
                "body" : text,
                "url" : article_link,
                "timestamp" : article_timestamp,
                "keywords" : article_keywords
            }

            # stores the article
            database.article_info.insert_one(data) # replace "article_info" with the name of the desired collection
            counter += 1
            print(article_title + " from " + title + " done")

    client.close() # closes MongoClient

# fetches 350 articles
def daily_fetch():
    global counter

    # fetches articles from high priority websites w/ the 350 article limit
    index = 0
    while counter <= 350:
        # breaks out of the loop if every website has been visited
        if index >= len(high_priority_url_list):
            break
        fetch(high_priority_url_list[index], high_priority_source_list[index])
        index += 1
    
    # fetches articles from lower priority websites w/ the 350 article limit
    index = 0
    while counter <= 350:
        if index >= len(lower_priority_url_list):
            break
        fetch(lower_priority_url_list[index], lower_priority_source_list[index])
        index += 1
    
    # fetches the rest of the 350 articles from the PTT stock board
    if counter < 350:
        num = 350 - counter
        PTT_scraper.fetch(num)

    # runs deduplication logic using tfidf
    deduplication.tfidf_comparison(connection_string, database_name, 1)

daily_fetch()
# schedules the daily fetch for the three times each day, in Taiwan's time zone
schedule.every().day.at("07:30", "Asia/Hong_Kong").do(daily_fetch)
schedule.every().day.at("13:30", "Asia/Hong_Kong").do(daily_fetch)
schedule.every().day.at("18:00", "Asia/Hong_Kong").do(daily_fetch)

# pauses the program while waiting for the scheduled fetches
while True:
    schedule.run_pending()
    time.sleep(1)