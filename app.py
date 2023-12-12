from flask import Flask, request, jsonify, render_template
from flask_cors import CORS 
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from transformers import pipeline
import spacy
#import Hugging Face model
pipe = pipeline("text-classification", "remzicam/privacy_intent")

app = Flask(__name__)
CORS(app)  # Add this line to enable CORS for all routes

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    data = request.get_json(force=True)
    url = data.get('url')

    # Load English tokenizer, tagger, parser, NER, and word vectors
    nlp = spacy.load("en_core_web_sm")

    #function that locates the link to the privacy policy on a given website
    def find_privacy_policy_link(url):
        # Send a GET request to the website
        response = requests.get(url)
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Find all <a> tags (links) in the page
        all_links = soup.find_all("a", href=True)
        
        # Search for links containing "privacy" or "policy" keywords
        privacy_policy_links = []
        for link in all_links:
            href = link["href"]
            text = link.get_text().lower()  # Get the text within the link and convert to lowercase for comparison
            if "privacy" in text or "privacy policy" in text:
                absolute_url = urljoin(url, href)  # Make the URL absolute
                privacy_policy_links.append(absolute_url)
        
        return privacy_policy_links

    privacy_links = find_privacy_policy_link(url)
    policy_link = privacy_links[0]

    def find_policy_section(url, pattern):
        # Fetch the HTML content from the URL
        response = requests.get(url)
        html_content = response.text

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find the header containing the specific search term
        header = soup.find('h1', string=re.compile(pattern, re.IGNORECASE))

        if header:
            # Find the next sibling elements until the next header (assumed structure)
            retention_section = []
            next_element = header.find_next_sibling()
            while next_element and next_element.name != 'h1':
                retention_section.append(next_element)
                next_element = next_element.find_next_sibling()

            # Combine the text from the section elements
            retention_text = ' '.join([element.get_text() for element in retention_section])

            return retention_text
        else:
            return

    def summarize_text(text):

        # Iterate through the text and add periods where needed
        for i in range(len(text) - 1):
            if text[i].islower() and text[i + 1].isupper():
                # Check if the current character is lowercase and the next is uppercase
                # Add a period after the lowercase character
                text = text[:i + 1] + '.' + text[i + 1:]

        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)

        #score the sentences in the document
        sentence_scores = {}
        for sent in doc.sents:
            sentence_scores[sent] = sum(token.similarity(token) for token in sent if not token.is_stop)

        # Sort sentences by their scores
        sorted_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)

        # Generate summary with top sentences
        num_sentences_in_summary = 1  # Set the number of sentences you want in the summary
        summary_sentences = [str(sent[0]) for sent in sorted_sentences[:num_sentences_in_summary]]

        # Join summary sentences into a single string
        summary = ' '.join(summary_sentences)
        
        #generate the overall privacy score
        score_dict = pipe(summary)[0]
        label = score_dict['label']
        score = score_dict['score']

        return summary, label, score
    
    total = []

    # Data Collection/Usage, Data Sharing/Disclosure, Data Storage/Retention, Data Security/Protection
    policy_list = [r'\bcollec\w+\b', r'\bshar\w+\b', r'\bretain\w*\b', r'\bsecur\w*\b']
    policy_title = {
        r'\bcollec\w+\b': "2.1 Data Collection", 
        r'\bshar\w+\b': "2.2 Data Sharing", 
        r'\bretain\w*\b': "2.3 Data Retention", 
        r'\bsecur\w*\b': "2.4 Data Security"
    }

    privacy_summary = []
    privacy_violations = []

    #for each policy category, summarize and score the section
    for i in policy_list:
        text = find_policy_section(policy_link, i)
        summary, label, score = summarize_text(text)
        privacy_summary.append(summary)
        total.append(score)

        #arbitrary parameter which defines what score is considered a privacy violation
        if score < 0.98:
            privacy_violations.append(policy_title[i])

    total_score = (sum(total)/len(total)) 
    rounded_score = str(round(total_score, 2)* 100) + "%"

    # Return analysis result to the extension
    return jsonify({'privacy_summary': privacy_summary, 'result': rounded_score, 'privacy_violations': privacy_violations})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)