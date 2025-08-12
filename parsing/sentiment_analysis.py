"""This program feeds the fetched information into OpenAI and provides the sentiment analysis
output for each article
"""

import asyncio
from openai import OpenAI, APITimeoutError, APIConnectionError, AsyncOpenAI
import json
import time

event_type_list : list[str] = [
    "earnings",
    "policy",
    "regulation",
    "merger_acquisition",
    "downgrade",
    "product_launch",
    "geopolitical",
    "macroeconomic_data",
    "litigation",
    "executive_change",
    "investment",
    "guidance_revision",
    "none"
]

tone_prompt : str = """

To determine tone:

Directional market implication is proven when at least 2 of the 3 following conditions are met: 
1. The article uses strong directional language (e.g. surges, misses, accelerates, downgraded), 
2. The event has market-level implication (e.g. affects sector outlook, macro policy, investor behavior), or 
3. There is a clear statement of expectation or sentiment from a named source (e.g. CEO, analyst, government official).

-If there is no directional market implication proven, label the sentiment tone as "neutral". 
-If there is directional market implication proven but the implication is not clearly positive or negative OR the implication is both positive and negative, label the sentiment tone as "neutral". 
-If there is directional market implication proven and it is clearly positive, label the sentiment tone as "bullish". If there is directional market implication proven and it is clearly negative, label the sentiment tone as "bearish". 
-If none of these conditions apply, make your own judgement and select the sentiment tone that best applies."""

confidence_prompt : str = """

To determine the confidence score: 

You will now answer 10 yes/no questions to assess how confident you are in your sentiment classification of the article.

Answer each question with "Yes" or "No" only.

Then, calculate your confidence score as:  
(Number of "Yes" answers) ÷ 10 → Return a float between 0.0 and 1.0

Here are your questions:
1. Is the sentiment direction (positive/negative) clearly implied by the article?
2. Does the article mention a price movement or valuation change?
3. Is there reference to performance versus expectation (e.g. beats, misses)?
4. Does the article include strong directional wording (e.g. surges, collapses)?
5. Is the event covered relevant to a broader market, not just internal news?
6. Is there a quote or opinion from a named source (e.g. analyst, executive)?
7. Would most readers interpret this as having market impact?
8. Is the timing of the event recent (within the past 72 hours)?
9. Are there multiple supporting data points or factual references?
10. Would this article be relevant for a trading alert?
After answering, output the total number of "Yes", and return the confidence score as a float between 0.0 and 1.0. Format the output as a json file, in the following format:

{
    "yes_answers" : "..."
    "confidence_score" : "..."
}"""

entities_prompt : str = """Extract all named entities mentioned in the following financial article.

Return a list of entities that includes:
- Company names
- Public institutions
- Key executives or analysts

Format your response in a json file as:
{
  "entities": ["TSMC", "NVIDIA", "Fed", "Elon Musk"]
}"""

event_type_prompt : str = f"""Given the news title and content, identify the main **event type** mentioned in the article.

Choose the most appropriate label from this list:
{event_type_list}

Return the event type as a single string.

If none applies, return "none"."""

output_json_format : str = """
{
    "tone" : "...",
    "topic": "...",
    "event_type": "...",
    "confidence": ...,
    "summary": "...",
    "evidence": "..."
}"""

system_prompt : str = f"""You are a financial news analyst. Given a headline and its content, determine:
- Overall sentiment tone: bullish / bearish / neutral {tone_prompt} 
- Topic classification (e.g., semiconductor, Fed policy, trade war)
- Event type (e.g., earnings, regulation, M&A, downgrade) {event_type_prompt}
- A confidence score (0–1) for your judgment
- A one-sentence explanation summarizing your reasoning
- A sentence quoted from the news that best supports your sentiment decision

Return all results in the following JSON format:
{output_json_format}"""

headline_content_prompt : str = """Return the headline and content in the following format:
News headline: {{title}}
News content: {{content}}"""

def get_response(client : OpenAI, system_prompt, content) -> str:
    num_tries = 0
    while num_tries < 3:
        try:
            main_response = client.chat.completions.create(
                    model = "gpt-4.1-nano",
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content},
                    ],
                    response_format = {"type": "json_object"}
                )
            break
        except APITimeoutError as timeout:
            print(f"openai timed out: {timeout}")
            num_tries += 1
        except APIConnectionError as connection_error:
            print(f"openai had a connection error: {connection_error}")
            num_tries += 1
    
    response = main_response.choices[0].message.content
    print(response)
    parsed_response = json.loads(response)
    return parsed_response

def analyze(article_collection, sentiment_collection, entity_collection, confidence_collection, start_index : int) -> None:
    documents = article_collection.find({})
    with OpenAI(timeout = 20.0) as AI_client:
        counter = start_index # for document naming
        sentiment_docs = [] # holds documents to add to MongoDB
        entity_docs = []
        confidence_docs = []
        for doc in documents[start_index:]:

            headline = doc["title"]
            content = doc["body"]

            # gets the result for the sentiment result
            parsed_sentiment_response = get_response(AI_client, system_prompt, 
                                                     f"Give me the output for an article using the language of the article, for which the headline is: {headline}, and the content is: {content}")
            parsed_sentiment_response.update({"id" : str(counter)})

            # gets the result for the confidence score detail
            parsed_confidence_response = get_response(AI_client, 
                                                      f"You are a financial news analyst analyzing an article. The headline is {headline}, and the content is: {content}", 
                                                      confidence_prompt)
            parsed_confidence_response.update({"id" : str(counter)})

            # gets the response for the entity match
            parsed_entities_response = get_response(AI_client, 
                                                    f"You are a financial news analyst analyzing an article. The headline is {headline}, and the content is: {content}",
                                                    entities_prompt)
            parsed_entities_response.update({"id" : str(counter)})

            parsed_sentiment_response["confidence"] = parsed_confidence_response["confidence_score"]

            
            sentiment_docs.append(parsed_sentiment_response)
            entity_docs.append(parsed_entities_response)
            confidence_docs.append(parsed_confidence_response)
            
            counter += 1
        
        print("inserting documents")
        sentiment_collection.insert_many(sentiment_docs)
        entity_collection.insert_many(entity_docs)
        confidence_collection.insert_many(confidence_docs)

    # closes cursor
    documents.close()

async def get_async_response(semaphore, client, system_prompt, content) -> str:
    print("get async response called")
    async with semaphore:
        try:
            response =  await client.chat.completions.create(
                        model = "gpt-4.1-nano",
                        messages = [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": content},
                        ],
                        response_format = {"type": "json_object"},
                        #max_completion_tokens = 32768,
                        timeout = 120.0
                    )
            print(response.choices[0].message.content)
            return response.choices[0].message.content
        except Exception as e:
            print(f"error getting openai response: {e}")
            return None

async def async_analyze(article_collection, sentiment_collection, entity_collection, confidence_collection, start_index : int):
    prompts = []
    documents = article_collection.find({})
    semaphore = asyncio.Semaphore(10)
    client = AsyncOpenAI()

    for doc in documents[start_index:]:
        headline = doc["title"]
        content = doc["body"]
        content_prompt_sentiment = f"Give me the output for an article using the language of the article, for which the headline is: {headline}, and the content is: {content}"
        system_prompt_2 = f"You are a financial news analyst analyzing an article. The headline is {headline}, and the content is: {content}"
        prompts.extend([[system_prompt, content_prompt_sentiment], [system_prompt_2, confidence_prompt], [system_prompt_2, entities_prompt]])
        
    print("creating tasks")
    tasks = [get_async_response(semaphore, client, prompt[0], prompt[1]) for prompt in prompts]
    print("getting results")
    
    print("awaiting")
    results = await asyncio.gather(*tasks)

    print("parsing results")
    parsed_results = [json.loads(result) for result in results]
    
    sentiment_responses = parsed_results[0::3]
    confidence_responses = parsed_results[1::3]
    entity_responses = parsed_results[2::3]

    for index, (sentiment, confidence, entities) in enumerate(zip(sentiment_responses, confidence_responses, entity_responses)):
        sentiment["confidence"] = confidence["confidence_score"]
        sentiment["id"] = index + start_index
        confidence["id"] = index + start_index
        entities["id"] = index + start_index

    print("inserting results")
    sentiment_collection.insert_many(sentiment_responses)
    confidence_collection.insert_many(confidence_responses)
    entity_collection.insert_many(entity_responses)

def start_async(article_collection, sentiment_collection, entity_collection, confidence_collection, start_index : int):
    asyncio.run(async_analyze(article_collection, sentiment_collection, entity_collection, confidence_collection, start_index))
        

if __name__ == "__main__":
    import os
    from pymongo import MongoClient # for uploading data to MongoDB

    connection_string : str = os.getenv("MONGODB_CONNECTION_STRING")
    database_name : str = "news_info" # replace with wanted database name
    Mongo_client = MongoClient(connection_string)
    database = Mongo_client[database_name]

    try:
        database.create_collection("sentiment_results")
    except Exception as e:
        print(f"Error creating collection: {e}")
    try:
        database.create_collection("entity_match_results")
    except Exception as e:
        print(f"Error creating collection: {e}")
    try:
        database.create_collection("confidence_score_details")
    except Exception as e:
        print(f"Error creating collection: {e}")

    sentiment_collection = database["sentiment_results"]
    entity_collection = database["entity_match_results"]
    confidence_collection = database["confidence_score_details"]
    article_collection = database["article_info"]

    start = time.perf_counter()
    asyncio.run(async_analyze(article_collection, sentiment_collection, entity_collection, confidence_collection, 0))
    #analyze(article_collection, sentiment_collection, entity_collection, confidence_collection, 0)
    end = time.perf_counter()
    total_time = end - start
    print(f"time taken: {total_time} seconds")