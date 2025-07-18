'''This program will fetch title, source, body, url, timestamp, and keywords from articles, fetching 350 at a time, 3 times daily.
Data is obtained primarily through RSS parsing, and then web scraping the PTT stock board with HTML. The data obtained is uploaded
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

# list of urls and source for higher quality websites, indexes of url and source correspond
high_priority_url_list = ["https://news.cnyes.com/rss/v1/news/category/tw_stock", "https://news.cnyes.com/rss/v1/news/category/all", "https://news.cnyes.com/rss/v1/news/category/headline", "https://www.moneydj.com/kmdj/RssCenter.aspx?svc=NW&fno=1&arg=X0000000", "https://tw.stock.yahoo.com/rss?category=tw-market"]
high_priority_source_list = ["鉅亨網 (Anue)", "鉅亨網 (Anue)", "鉅亨網 (Anue)", "MoneyDJ 理財網", "Yahoo 奇摩股市"]

# list of urls and source for lower quality websites, indexes of url and source correspond
lower_priority_url_list = ["https://cmsapi.businessweekly.com.tw/?CategoryId=efd99109-9e15-422e-97f0-078b21322450&TemplateId=8E19CF43-50E5-4093-B72D-70A912962D55", "https://techorange.com/feed/", "https://www.inside.com.tw/feed/rss", "https://feeds.feedburner.com/rsscna/finance"]
lower_priority_source_list = ["商業週刊", "TechOrange 科技報橘", "Inside (科技媒體)", "中央社財經 (CNA)"]

counter = 0 # counts the number of articles fetched

# fetches articles from one source
def fetch(url, title):
    # connects to the MongoDB database
    client = MongoClient("mongodb+srv://madelynsk7:vy97caShIMZ2otO6@testcluster.aosckrl.mongodb.net/") # replace string with the wanted connection string
    database = client["news_info"] # replace string with the name of the wanted database

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

            match title:
                case "鉅亨網 (Anue)":
                    try:
                        response = requests.get(article_link)
                    except:
                        continue

                    html_content = response.text

                    soup = BeautifulSoup(html_content, "xml")

                    article = soup.find(id = "article-container")
                    paragraphs = article.find_all("p")

                    
                    for i in paragraphs:
                        text += i.get_text()
                case "MoneyDJ 理財網":
                    article = Article(article_link)
                    article.download()
                    article.parse
                    text = article.text
                case "Yahoo 奇摩股市":
                    try:
                        response = requests.get(article_link)
                    except:
                        continue

                    html_content = response.text

                    soup = BeautifulSoup(html_content, "xml")

                    article = soup.find("article")
                    paragraphs = article.find_all("p")

                    
                    for i in paragraphs:
                        text += i.get_text()
                case "商業週刊":
                    article = Article(article_link)
                    article.download()
                    article.parse
                    text = article.text
                case "TechOrange 科技報橘":
                    article = Article(article_link)
                    article.download()
                    article.parse
                    text = article.text  
                case "Inside (科技媒體)":
                    article = Article(article_link)
                    article.download()
                    article.parse
                    text = article.text
                case "中央社財經 (CNA)":
                    article = Article(article_link)
                    article.download()
                    article.parse
                    text = article.text
            
            article_keywords = [] # list to hold the keywords found in the article
            
            # loops through the keyword filter set
            file.seek(0)
            csv_reader = csv.reader(file)
            for row in csv_reader:
                if row: #check if the row isn't empty
                    keyword = row[0]

                    # adds the article keyword if one is found
                    if keyword in article_title or keyword in text:
                        article_keywords.append(keyword)

            # creates the file to be stored
            data = {
                "title" : article_title,
                "source" : title,
                "body" : article.text,
                "url" : article_link,
                "timestamp" : article_timestamp,
                "keywords" : article_keywords
            }

            # stores the article
            database.article_info.insert_one(data) # replace "article_info" with the name of the desired collection
            counter += 1

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

    print(counter)

daily_fetch()
# schedules the daily fetch for the three times each day, in Taiwan's time zone
schedule.every().day.at("07:30", "Asia/Hong_Kong").do(daily_fetch)
schedule.every().day.at("13:30", "Asia/Hong_Kong").do(daily_fetch)
schedule.every().day.at("18:00", "Asia/Hong_Kong").do(daily_fetch)

# pauses the program while waiting for the scheduled fetches
while True:
    schedule.run_pending()
    time.sleep(1)