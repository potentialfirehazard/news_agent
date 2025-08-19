"""This program contains the deduplication logic for the saved articles. There is a function for TD-IDF vectorization and
one for SBERT vectorization, and ultimately cosine similarity is used to determine similarity. Articles over the determined
similarity threshold will be deleted.
"""

#print("importing vectorizer")
from sklearn.feature_extraction.text import TfidfVectorizer
#print("importing cosine similarity")
from sklearn.metrics.pairwise import cosine_similarity
#print("importing string")
import string
#print("importing sentence transformers")
from sentence_transformers import SentenceTransformer
import logging
import time

logging.basicConfig(
    filename = "deduplication.log", 
    level = logging.INFO, 
    format = "%(asctime)s - %(levelname)s - %(message)s"
)

# removes punctuation and formatting text from a document
def clean(document : str) -> str:
    translator = str.maketrans("", "", string.punctuation)
    cleaned_doc = document.translate(translator)
    cleaned_doc = cleaned_doc.replace("\n", "")
    return cleaned_doc

# removes all documents considered duplicates from the MongoDB database w/ td-idf logic
def tfidf_comparison(collection, threshold : int) -> None:
    start = time.perf_counter()
    
    vectorizer = TfidfVectorizer() # creates a vectorizer for the document
    
    # gets all the documents from the database
    documents = collection.find()
    cleaned_texts = []
    ids = []

    # saves the cleaned body text and id of every document
    for doc in documents:
        text = doc["body"]
        id = doc["_id"]
        cleaned_texts.append(clean(text))
        ids.append(id)
    
    # creates a matrix of each text vectorized
    tfidf_matrix = vectorizer.fit_transform(cleaned_texts)

    duplicate_article_ids = [] # stores ids of articles marked as duplicates

    # loops through indexes of each stored text
    for index, current_id in enumerate(ids):
        
        # skips the article if it has been marked as a duplicate
        if current_id in duplicate_article_ids:
            continue

        # creates a cosine similarity matrix between the current text and the rest of the texts
        similarities = cosine_similarity(tfidf_matrix[index][0], tfidf_matrix)

        counter = 0 # counts the number of similar articles

        # loops through each index in the cosine similarity matrix
        for score_index, (similarity_score, article_id) in enumerate(zip(similarities[0], ids)): # using similarities[0] b/c there is only one row in the matrix
            
            # checks if the similarity index is at or above the threshold
            if similarity_score >= threshold:
                
                # finds the id of the duplicate and adds it to the list of duplicates
                duplicate_id = article_id
                duplicate_article_ids.append(duplicate_id)
                counter += 1
            
        # removes one of the duplicates so one instance of the article is preserved
        if counter > 0:
            duplicate_article_ids.pop((len(duplicate_article_ids) - counter))

    # deletes every id marked to be deleted
    for id in duplicate_article_ids:

        article = collection.find_one({"_id" : id})
        title = article["title"]
        logging.info(f"deleting article {title}")
        collection.delete_one({"_id" : id})
        print("deleting duplicate " + str(id))
    
    # resets ids for the new number of documents
    index = 0
    documents = collection.find()
    for doc in documents:
        collection.update_one({"_id" : doc["_id"]}, {"$set": {"id": index}})
        index += 1

    # closes cursor
    documents.close()
    end = time.perf_counter()
    logging.info(f"Time taken for TFIDF deduplication: {end - start}")

# removes all documents considered duplicates with sbert
def sbert_comparison(collection, threshold : int) -> None:
    start = time.perf_counter()

    vectorizer = SentenceTransformer("all-MiniLM-L6-v2") # creates a vectorizer for the document
    
    # gets all the documents from the database
    documents = collection.find()
    cleaned_texts = []
    ids = []

    # saves the cleaned body text and id of every document
    for doc in documents:
        text = doc["body"]
        id = doc["_id"]
        cleaned_texts.append(clean(text))
        ids.append(id)
    
    # creates a matrix of each text vectorized
    vectorized_docs = vectorizer.encode(cleaned_texts)
    print(vectorized_docs)

    duplicate_article_ids = [] # stores ids of articles marked as duplicates

    # loops through indexes of each stored text
    for index, current_id in enumerate(ids):
        
        # skips the article if it has been marked as a duplicate
        if current_id in duplicate_article_ids:
            continue
        
        current_doc = vectorized_docs[index]

        # creates a cosine similarity matrix between the current text and the rest of the texts
        similarities = cosine_similarity(current_doc.reshape(1, -1), vectorized_docs)
        print(similarities)

        counter = 0
        # loops through each index in the cosine similarity matrix
        for score_index, (similarity_score, article_id) in enumerate(zip(similarities[0], ids)): # using similarities[0] b/c there is only one row in the matrix
            
            # checks if the similarity index is at or above the threshold
            if similarity_score >= threshold:
                
                # finds the id of the duplicate and adds it to the list of duplicates
                duplicate_id = article_id
                duplicate_article_ids.append(duplicate_id)
                counter += 1
            
        # removes one of the duplicates so one instance of the article is preserved
        if counter > 0:
            print(len(duplicate_article_ids) - counter)
            duplicate_article_ids.pop((len(duplicate_article_ids) - counter))

    # deletes every id marked to be deleted
    for id in duplicate_article_ids:

        collection.delete_one({"_id" : id})
        print("deleting duplicate " + str(id))
    
    # resets ids for the new number of documents
    index = 0
    documents = collection.find()
    for doc in documents:
        collection.update_one({"_id" : doc["_id"]}, {"$set": {"id": "index"}})
        index += 1
    
    # closes cursor
    documents.close()
    end = time.perf_counter()
    logging.info(f"Time taken for SBERT deduplication: {end - start}")

if __name__ == "__main__":
    import os
    from pymongo import MongoClient

    connection_string = os.getenv("MONGODB_CONNECTION_STRING")
    client = MongoClient(connection_string)
    sbert_comparison(client, "news_info", 1)