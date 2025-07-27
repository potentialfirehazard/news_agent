from openai import OpenAI
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
tone_prompt = "\n\nTo determine tone:\nDirectional market implication is proven when at least 2 of the 3 following conditions are met: 1. The article uses strong directional language (e.g. surges, misses, accelerates, downgraded), 2. The event has market-level implication (e.g. affects sector outlook, macro policy, investor behavior), or 3. There is a clear statement of expectation or sentiment from a named source (e.g. CEO, analyst, government official). If there is no directional market implication proven, label the sentiment tone as \"neutral\". If there is directional market implication proven but the implication is not clearly positive or negative OR the implication is both positive and negative, label the sentiment tone as \"neutral\". If there is directional market implication proven and it is clearly positive, label the sentiment tone as \"bullish\". If there is directional market implication proven and it is clearly negative, label the sentiment tone as \"bearish\". If none of these conditions apply, make your own judgement and select the sentiment tone that best applies."
confidence_prompt = "\n\nTo determine the confidence score: You will now answer 10 yes/no questions to assess how confident you are in your sentiment classification of the article.\n\nAnswer each question with \"Yes\" or \"No\" only.\n\nThen, calculate your confidence score as:  \n(Number of \"Yes\" answers) ÷ 10 → Return a float between 0.0 and 1.0\n\nHere are your questions:\n1. Is the sentiment direction (positive/negative) clearly implied by the article?\n2. Does the article mention a price movement or valuation change?\n3. Is there reference to performance versus expectation (e.g. beats, misses)?\n4. Does the article include strong directional wording (e.g. surges, collapses)?\n5. Is the event covered relevant to a broader market, not just internal news?\n6. Is there a quote or opinion from a named source (e.g. analyst, executive)?\n7. Would most readers interpret this as having market impact?\n8. Is the timing of the event recent (within the past 72 hours)?\n9. Are there multiple supporting data points or factual references?\n10. Would this article be relevant for a trading alert?\n\nAfter answering, output the total number of \"Yes\", and return the confidence score as a float between 0.0 and 1.0. Format the output as a json file."
entities_prompt = "Extract all named entities mentioned in the following financial article.\n\nReturn a list of entities that includes:\n- Company names\n- Public institutions\n- Key executives or analysts\n\nFormat your response in a json file as:\n{\n  \"entities\": [\"TSMC\", \"NVIDIA\", \"Fed\", \"Elon Musk\"]\n}"
event_type_prompt = "You are a financial news analyst.\n\nGiven the news title and content, identify the main **event type** mentioned in the article.\n\nChoose the most appropriate label from this list:\n" + str(event_type_list) + "[previous JSON list you can see above]""\n\nReturn the event type as a single string.\n\nIf none applies, return \"none\"."
main_prompt = "You are a financial news analyst. Given a headline and its content, determine:\n- Overall sentiment tone: bullish / bearish / neutral\n" + tone_prompt + "\n- Topic classification (e.g., semiconductor, Fed policy, trade war)\n- Event type (e.g., earnings, regulation, M&A, downgrade)\n- A confidence score (0–1) for your judgment\n" + confidence_prompt + "\n- A one-sentence explanation summarizing your reasoning\n- A sentence quoted from the news that best supports your sentiment decision\n\nReturn all results in the following JSON format:\n{\n  \"tone\": \"...\",\n  \"topic\": \"...\",\n  \"event_type\": \"...\",\n  \"confidence\": ...,\n  \"summary\": \"...\",\n  \"evidence\": \"...\"\n}"
prompt_cont = "Return the headline and content in the following format:\nNews headline: {{title}}\nNews content: {{content}}"
headline = "智易Q2動態避險控制匯損 財報亮眼股價重返200元大關"
content = "網通廠智易 (3596-TW)23 日公告第二季財報，透過動態避險策略，成功將新台幣升值衝擊控制在 0.92 億元，營收 134.62 億元創歷年同期新高，每股盈餘 3.02 元。財報表現亮眼激勵股價強勢反彈，今日重返 200 元大關，終場收 211 元，漲近 8%，成交量 4998 張，較前一日放大逾 7 倍。智易第二季營收 134.62 億元，季增 6%、年增 10.6%，累計上半年營收 261.65 億元，年增 5.9%，雙雙刷新同期紀錄；匯率風險管控方面，智易採行動態避險策略，將第二季匯損控制在合理範圍。外幣兌換損失 0.75 億元，避險工具損失 0.17 億元，總計匯損約 0.92 億元，遠低於市場預期，稅後淨利仍達 6.65 億元，年增 13.7%。歐洲電信商積極推動 10G PON 搭配 Wi-Fi 7 升級方案，加上 5G FWA 需求從北美擴展至歐洲及亞洲市場，帶動智易營運明顯回神。印度寬頻基礎建設持續推進，亦為營收成長提供支撐。展望後市，智易受惠於客戶持續推出新規格產品線，包括 Wi-Fi 7 與 10G PON 等高附加價值產品。法人預期 Wi-Fi 7 產品出貨比重今年可達 30%，將有助提升整體毛利率表現。"
connection_string = "mongodb+srv://madelynsk7:vy97caShIMZ2otO6@testcluster.aosckrl.mongodb.net/" # replace with wanted connection string
database_name = "news_info" # replace with wanted database name

# connects to OpenAI and MongoDB
AI_client = OpenAI() # OPENAI_API_KEY set as environment variable
Mongo_client = MongoClient(connection_string)
database = Mongo_client[database_name]
documents = database.article_info.find({})

'''for doc in documents:

    headline = doc["title"]
    content = doc["body"]

    response = AI_client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": main_prompt},
                {"role": "user", "content": "Give me the output for an article in the language of the article, for which the headline is: " + headline + ", and the content is: " + content},
            ]
        )

    print(response.choices[0].message.content)'''

# gets the result for the sentiment result
main_response = AI_client.chat.completions.create(
        model = "gpt-4.1-nano",
        messages = [
            {"role": "system", "content": main_prompt},
            {"role": "user", "content": "Give me the output for an article using the language of the article, for which the headline is: " + headline + ", and the content is: " + content},
        ],
        response_format = {"type": "json_object"}
    )

# puts the response into json format
response = main_response.choices[0].message.content
print(response)
parsed_sentiment_response = json.loads(response)

# gets the result for the confidence score detail
confidence_response = AI_client.chat.completions.create(
        model = "gpt-4.1-nano",
        messages = [
            {"role": "system", "content": "You are a financial news analyst analyzing an article. The headline is " + headline + ", and the content is: " + content},
            {"role": "user", "content": confidence_prompt},
        ],
        response_format = {"type": "json_object"}
    )

# puts the response into json format
response = confidence_response.choices[0].message.content
print(response)
parsed_confidence_response = json.loads(response)

# gets the response for the entity match
entities_response = AI_client.chat.completions.create(
        model = "gpt-4.1-nano",
        messages = [
            {"role": "system", "content": "You are a financial news analyst analyzing an article. The headline is " + headline + ", and the content is: " + content},
            {"role": "user", "content": entities_prompt},
        ],
        response_format = {"type": "json_object"}
    )

# puts the response into json format
response = entities_response.choices[0].message.content
print(response)
parsed_entities_response = json.loads(response)


with open("news agent\data\sentiment_result.json", mode = "w", encoding = "utf-8", newline = "") as file:
    json.dump(parsed_sentiment_response, file, indent = 4, ensure_ascii = False)

with open("news agent\data\confidence_score_detail.json", mode = "w", encoding = "utf-8", newline = "") as file:
    json.dump(parsed_confidence_response, file, indent = 4, ensure_ascii = False)

with open("news agent\data\entity_match_result.json", mode = "w", encoding = "utf-8", newline = "") as file:
    json.dump(parsed_entities_response, file, indent = 4, ensure_ascii = False)
