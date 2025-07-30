'''This program is an HTML web scraper that obtains title, source, body, url, timestamp, and keywords from articles from
the PTT Stock Board. THe data obtained is uploaded to MongoDB. This program is specific to the PTT Stock Board, and cannot
be used for other websites due to different HTML structures.'''

from bs4 import BeautifulSoup # for HTML parsing
import bs4 # for HTML parsing
import requests # to get the HTML of websites
import csv # to parse the keyword filter set
from pymongo import MongoClient # to upload to MongoDB

# gets the BeautifulSoup object of the webpage for scraping
def get_article(url):
    response = requests.get(url)
    html_content = response.text

    return BeautifulSoup(html_content, "lxml")

# gets the body text of a PTT Stock Board Post
def get_body_text(soup):

    article = soup.find_all(class_ = "article-metaline") # uses article-metaline tags as starting point for body text
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

    return(text)

# fetches a specified number of articles from the PTT Stock Board
def fetch(client, database_name, number):
    
    database = client[database_name]
    counter = 0 # counts the number of articles fetched
    url = "https://www.ptt.cc/bbs/stock/index.html"
    cont = True

    # opens keyword filter set
    with open("news_agent\data\keyword_filter_set_zh.csv", mode = "r", encoding = "utf-8", newline = "") as file:

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
                            time = i.find(class_ = "article-meta-value").get_text()
                    
                    # finds body text
                    text = get_body_text(article)
                    
                    article_keywords = []
                    
                    # loops through the keyword filter list
                    csv_reader = csv.reader(file)
                    for row in csv_reader:
                        if row: # check if the row isn't empty
                            keyword = row[0]
                            if keyword in info.get_text() or keyword in text: # adds the keyword to the list if it is found
                                article_keywords.append(keyword)
                    
                    # creates the file to be stored
                    data = {
                        "title" : info.get_text(),
                        "source" : "PTT Stock Board",
                        "body" : text,
                        "url" : article_link,
                        "timestamp" : time,
                        "keywords" : article_keywords
                    }

                    # adds the file to the database
                    database.article_info.insert_one(data)
                    counter += 1
                    
                    # stops fetching if the number of articles needed is reached
                    if counter >= number:
                        cont = False
                        break

            # finds all the buttons for navigating the page
            buttons = get_article(url).find_all(class_ = "btn wide")

            # finds the button to go to the next page and sets the link for parsing to the next page
            for i in buttons:
                    if i.get_text() == "‹ 上頁":
                        url = "https://www.ptt.cc" + i.get("href")
