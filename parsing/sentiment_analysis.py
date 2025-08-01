"""This program feeds the fetched information into OpenAI and provides the sentiment analysis
output for each article"""

from openai import OpenAI, APITimeoutError, APIConnectionError
from pymongo import MongoClient # for uploading data to MongoDB
import json

event_type_list = [
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

tone_prompt = """

To determine tone:

Directional market implication is proven when at least 2 of the 3 following conditions are met: 
1. The article uses strong directional language (e.g. surges, misses, accelerates, downgraded), 
2. The event has market-level implication (e.g. affects sector outlook, macro policy, investor behavior), or 
3. There is a clear statement of expectation or sentiment from a named source (e.g. CEO, analyst, government official).

-If there is no directional market implication proven, label the sentiment tone as "neutral". 
-If there is directional market implication proven but the implication is not clearly positive or negative OR the implication is both positive and negative, label the sentiment tone as "neutral". 
-If there is directional market implication proven and it is clearly positive, label the sentiment tone as "bullish". If there is directional market implication proven and it is clearly negative, label the sentiment tone as "bearish". 
-If none of these conditions apply, make your own judgement and select the sentiment tone that best applies."""

confidence_prompt = """

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

entities_prompt = """Extract all named entities mentioned in the following financial article.

Return a list of entities that includes:
- Company names
- Public institutions
- Key executives or analysts

Format your response in a json file as:
{
  "entities": ["TSMC", "NVIDIA", "Fed", "Elon Musk"]
}"""

event_type_prompt = f"""Given the news title and content, identify the main **event type** mentioned in the article.

Choose the most appropriate label from this list:
{event_type_list}

Return the event type as a single string.

If none applies, return "none"."""

output_json_format = """
{
    "tone" : "...",
    "topic": "...",
    "event_type": "...",
    "confidence": ...,
    "summary": "...",
    "evidence": "..."
}"""

system_prompt = f"""You are a financial news analyst. Given a headline and its content, determine:
- Overall sentiment tone: bullish / bearish / neutral {tone_prompt} 
- Topic classification (e.g., semiconductor, Fed policy, trade war)
- Event type (e.g., earnings, regulation, M&A, downgrade) {event_type_prompt}
- A confidence score (0–1) for your judgment
- A one-sentence explanation summarizing your reasoning
- A sentence quoted from the news that best supports your sentiment decision

Return all results in the following JSON format:
{output_json_format}"""

headline_content_prompt = """Return the headline and content in the following format:
News headline: {{title}}
News content: {{content}}"""

connection_string = "mongodb+srv://madelynsk7:vy97caShIMZ2otO6@testcluster.aosckrl.mongodb.net/" # replace with wanted connection string
database_name = "news_info" # replace with wanted database name

# connects to OpenAI and MongoDB
#AI_client = OpenAI() # OPENAI_API_KEY set as environment variable
Mongo_client = MongoClient(connection_string)

def analyze(Mongo_client, database_name, start_index):
    database = Mongo_client[database_name]
    documents = database.article_info.find({})
    with OpenAI(timeout = 20.0) as AI_client:
        counter = start_index
        for doc in documents[start_index:]:

            headline = doc["title"]
            content = doc["body"]

            # gets the result for the sentiment result
            num_tries = 0
            while num_tries < 3:
                try:
                    main_response = AI_client.chat.completions.create(
                            model = "gpt-4.1-nano",
                            messages = [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": f"Give me the output for an article using the language of the article, for which the headline is: {headline}, and the content is: {content}"},
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


            # changes the response string to a dictionary
            response = main_response.choices[0].message.content
            print(response)
            parsed_sentiment_response = json.loads(response)
            parsed_sentiment_response.update({"_id" : "sentiment_result_" + str(counter)})

            # gets the result for the confidence score detail
            confidence_response = AI_client.chat.completions.create(
                    model = "gpt-4.1-nano",
                    messages = [
                        {"role": "system", "content": "You are a financial news analyst analyzing an article. The headline is " + headline + ", and the content is: " + content},
                        {"role": "user", "content": confidence_prompt},
                    ],
                    response_format = {"type": "json_object"}
                )

            # changes the response string to a dictionary
            response = confidence_response.choices[0].message.content
            print(response)
            parsed_confidence_response = json.loads(response)
            parsed_confidence_response.update({"_id" : "confidence_score_detail_" + str(counter)})

            # gets the response for the entity match
            entities_response = AI_client.chat.completions.create(
                    model = "gpt-4.1-nano",
                    messages = [
                        {"role": "system", "content": "You are a financial news analyst analyzing an article. The headline is " + headline + ", and the content is: " + content},
                        {"role": "user", "content": entities_prompt},
                    ],
                    response_format = {"type": "json_object"}
                )

            # changes the response string to a dictionary
            response = entities_response.choices[0].message.content
            print(response)
            parsed_entities_response = json.loads(response)
            parsed_entities_response.update({"_id" : "entity_match_result_" + str(counter)})

            parsed_sentiment_response["confidence"] = parsed_confidence_response["confidence_score"]

            print("inserting documents")
            database.sentiment_analysis.insert_one(parsed_sentiment_response)
            database.sentiment_analysis.insert_one(parsed_confidence_response)
            database.sentiment_analysis.insert_one(parsed_entities_response)
            
            counter += 1
    
    # closes cursor
    documents.close()

#analyze(Mongo_client, database_name, 64)