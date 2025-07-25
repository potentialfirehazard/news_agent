from pymongo import MongoClient # for uploading data to MongoDB
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import string
from sentence_transformers import SentenceTransformer

# removes punctuation and formatting text from a document
def clean(document):
    translator = str.maketrans("", "", string.punctuation)
    cleaned_doc = document.translate(translator)
    cleaned_doc = cleaned_doc.replace("\n", "")
    return cleaned_doc

# removes all documents considered duplicates from the MongoDB database w/ td-idf logic
def tfidf_comparison(connection_string, database_name, threshold):
    # connects to the database
    client = MongoClient(connection_string)
    database = client[database_name]
    vectorizer = TfidfVectorizer() # creates a vectorizer for the document
    
    # gets all the documents from the database
    documents = database.article_info.find()
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
    for index in range((len(cleaned_texts))):
        
        # skips the article if it has been marked as a duplicate
        if ids[index] in duplicate_article_ids:
            continue

        # creates a cosine similarity matrix between the current text and the rest of the texts
        similarities = cosine_similarity(tfidf_matrix[index][0], tfidf_matrix)

        counter = 0
        # loops through each index in the cosine similarity matrix
        for score_index in range((len(similarities[0]))): # using similarities[0] b/c there is only one row in the matrix
            
            # checks if the similarity index is at or above the threshold
            if similarities[0][score_index] >= threshold:
                
                # finds the id of the duplicate and adds it to the list of duplicates
                duplicate_id = ids[score_index]
                duplicate_article_ids.append(duplicate_id)
                counter += 1
            
        # removes one of the duplicates so one instance of the article is preserved
        if counter > 0:
            print(len(duplicate_article_ids) - counter)
            duplicate_article_ids.pop((len(duplicate_article_ids) - counter))

    # deletes every id marked to be deleted
    for id in duplicate_article_ids:

        database.article_info.delete_one({"_id" : id})
        print("deleting duplicate " + str(id))
    
    # closes MongoClient
    client.close()

# removes all documents considered duplicates with sbert
def sbert_comparison(connection_string, database_name, threshold):
    # connects to the database
    client = MongoClient(connection_string)
    database = client[database_name]
    vectorizer = SentenceTransformer("all-MiniLM-L6-v2") # creates a vectorizer for the document
    
    # gets all the documents from the database
    documents = database.article_info.find()
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
    for index in range((len(cleaned_texts))):
        
        # skips the article if it has been marked as a duplicate
        if ids[index] in duplicate_article_ids:
            continue
        
        current_doc = vectorized_docs[index]

        # creates a cosine similarity matrix between the current text and the rest of the texts
        similarities = cosine_similarity(current_doc.reshape(1, -1), vectorized_docs)
        print(similarities)

        counter = 0
        # loops through each index in the cosine similarity matrix
        for score_index in range((len(similarities[0]))):
            
            # checks if the similarity index is at or above the threshold
            if similarities[0][score_index] >= threshold:
                print("duplicate found")
                
                # finds the id of the duplicate and adds it to the list of duplicates
                duplicate_id = ids[score_index]
                duplicate_article_ids.append(duplicate_id)
                counter += 1
            
        # removes one of the duplicates so one instance of the article is preserved
        if counter > 0:
            print(len(duplicate_article_ids) - counter)
            duplicate_article_ids.pop((len(duplicate_article_ids) - counter))

    # deletes every id marked to be deleted
    for id in duplicate_article_ids:

        database.article_info.delete_one({"_id" : id})
        print("deleting duplicate " + str(id))
    
    # closes MongoClient
    client.close()

sbert_comparison("mongodb+srv://madelynsk7:vy97caShIMZ2otO6@testcluster.aosckrl.mongodb.net/", "news_info", 1)