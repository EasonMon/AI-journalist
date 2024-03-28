import requests
import newspaper
from newspaper import Article
import ast
from http import HTTPStatus
import dashscope
import json
from serpapi import GoogleSearch

dashscope.api_key="YOUR_API_KEY" #https://dashscope.console.aliyun.com/apiKey
GOOGLE_API_KEY = "YOUR_API_KEY" #https://serpapi.com/dashboard

def get_search_terms_qw(topic):
    messages = [
        {"role": "system", "content": f"You are a world-class journalist. Generate a list of 2 search terms to search for to research and write an article about the topic."},
        {"role": "user" , "content": f"Please provide a list of 2 search terms related to '{topic}' for researching and writing an article. Respond with the search terms in a Python-parseable list, separated by commas."},
    ]
    response = dashscope.Generation.call(
        model='qwen-turbo',
        messages=messages,
        result_format='message',  # set the result to be "message" format.
    )
    # The response status_code is HTTPStatus.OK indicate success,
    # otherwise indicate request is failed, you can get error code
    # and message from code and message.
    if response.status_code == HTTPStatus.OK:
        data = response.output
        response_text = data['choices'][0]['message']['content']
        search_terms = json.loads(response_text)
        print(search_terms)
        return search_terms
    else:
        print(response.code)  # The error code.
        print(response.message)  # The error message.

def get_search_results(search_term):
    search = GoogleSearch({
        "q": search_term, 
        "location": "Austin,Texas",
        "api_key": GOOGLE_API_KEY
    })
    response = search.get_dict()
    data = response.get('organic_results')
    # print(search_term)
    # print(data)
    return data

def select_relevant_urls(search_results):
    if search_results is None:  # Check if search_results is None
        print("No search results found.")
        return []
    elif not search_results:  # Check if search_results is an empty list
        print("No search results found.")
        return []
    search_results_text = "\n".join([f"{i+1}. {result['link']}" for i, result in enumerate(search_results)])
    messages = [
        {"role": "system", "content": f"You are a journalist assistant. From the given search results, select the URLs that seem most relevant and informative for writing an article on the topic."},
        {"role": "user", "content": f"Search Results:\n{search_results_text}\n\nPlease select the numbers of the URLs that seem most relevant and informative for writing an article on the topic. Respond with the numbers in a Python-parseable list, Specially, Respond only by Python-parseable list and separated by commas."}
    ]

    response = dashscope.Generation.call(
        model='qwen-turbo',
        messages=messages,
        result_format='message',  # set the result to be "message" format.
    )

    data = response.output
    response_text = data['choices'][0]['message']['content']
    numbers = ast.literal_eval(response_text)
    relevant_indices = [int(num) - 1 for num in numbers]
    relevant_urls = [search_results[i]['link'] for i in relevant_indices]
    return relevant_urls

def get_article_text(url):
    article = Article(url)
    article.download()
    article.parse()
    return article.text

def write_article(topic, article_texts):

    combined_text = "\n\n".join(article_texts)
    
    if len(combined_text) > 5500: # qw-turbo limit 6000
        truncated_combined_text = combined_text[:5500]
        truncated_article_texts = truncated_combined_text.split("\n\n")
        print("The combined article texts have been truncated to fit the limit (5500 characters).")
    else:
        truncated_article_texts = article_texts
        print("The total length of article texts is within the limit.")

    messages = [
        {"role": "system", "content": f"You are a journalist. Write a high-quality, NYT-worthy article on the given topic based on the provided article texts. The article should be well-structured, informative, and engaging."},
        {"role": "user", "content": f"Topic: {topic}\n\nArticle Texts:\n{truncated_article_texts}\n\nPlease write a high-quality, NYT-worthy article on the topic based on the provided article texts. The article should be well-structured, informative, and engaging. Ensure the length is at least as long as a NYT cover story -- at a minimum, 15 paragraphs."}
    ]

    response = dashscope.Generation.call(
        model='qwen-turbo',
        messages=messages,
        result_format='message',  # set the result to be "message" format.
    )

    # print(response)
    data = response.output

    if data is None:  # Check if search_results is None
        print("No results.")
        return ''
    elif not data:  # Check if search_results is an empty list
        print("No results.")
        return ''
    article = data['choices'][0]['message']['content']
    return article

    # response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data)
    # article = response.json()['content'][0]['text']
    # return article

def edit_article(article):

    messages = [
        {"role": "system", "content": f"You are an editor. Review the given article and provide suggestions for improvement. Focus on clarity, coherence, and overall quality."},
        {"role": "user", "content": f"Article:\n{article}\n\nPlease review the article and provide suggestions for improvement. Focus on clarity, coherence, and overall quality."}
    ]

    response = dashscope.Generation.call(
        model='qwen-turbo',
        messages=messages,
        result_format='message',  # set the result to be "message" format.
    )

    data = response.output
    suggestions = data['choices'][0]['message']['content']

    messages = [
        {"role": "system", "content": f"You are an editor. Rewrite the given article based on the provided suggestions for improvement."},
        {"role": "user", "content": f"Original Article:\n{article}\n\nSuggestions for Improvement:\n{suggestions}\n\nPlease rewrite the article based on the provided suggestions for improvement."}
    ]

    data = response.output
    edited_article = data['choices'][0]['message']['content']

    return edited_article

# User input
topic = input("Init：Enter a topic to write about: ")
do_edit = input("Init：After the initial draft, do you want an automatic edit? This may improve performance, but is slightly unreliable. Answer 'yes' or 'no'.")


# Generate search terms
search_terms = get_search_terms_qw(topic)
print(f"\nPart1/6.Search Terms for '{topic}':")
print(", ".join(search_terms))

# Perform searches and select relevant URLs
relevant_urls = []
for term in search_terms:
    search_results = get_search_results(term)
    urls = select_relevant_urls(search_results)
    relevant_urls.extend(urls)

print('Part2/6.Relevant URLs to read:', relevant_urls)

# Get article text from relevant URLs
article_texts = []
for url in relevant_urls:
  try:
    text = get_article_text(url)
    if len(text) > 75:
      article_texts.append(text)
  except:
    pass

print('Part3/6.Articles to reference:', article_texts)

print('\n\nPart4/6.Writing article...')
# Write the article
article = write_article(topic, article_texts)
print("\nPart5/6.Generated Article:")
print(article)

if 'y' in do_edit:
  # Edit the article
  edited_article = edit_article(article)
  print("\nPart6/6.Edited Article:")
  print(edited_article)
