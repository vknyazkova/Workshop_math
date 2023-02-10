from flask import Flask, render_template, request
import spacy
import os.path
from collections import namedtuple

from utils import filter_selected_sentences, create_query_info, create_sentences_info, create_full_link
from database import DBHandler


app = Flask(__name__)
nlp = spacy.load('ru_core_news_sm')
DB_PATH = os.path.abspath('math_corpus_database.db')


@app.route('/')
def main_page():
    return render_template('home.html')


@app.route('/result', methods=['POST', 'GET'])
def result():
    if request.method == "GET":
        return render_template("home.html")

    user_request = request.form['text']

    query_info = create_query_info(user_request, nlp, DB_PATH)

    db = DBHandler(DB_PATH)

    selected_sentences = db.select_sentences(query_info.lemmatized.split(' '))
    SentenceInfo = namedtuple('SentenceInfo', ['id', 'sent', 'lemmatized', 'link'])
    selected_sentences = [SentenceInfo(s[0], s[1], s[2], create_full_link(s[3], s[4])) for s in selected_sentences]
    matching_sentences = filter_selected_sentences(selected_sentences, query_info.lemmatized.split(' '))

    sents_info = create_sentences_info(matching_sentences, query_info, DB_PATH)

    print(query_info)
    print(sents_info)
    return render_template('result1.html', query_info=query_info, sents_info=sents_info)


if __name__ == '__main__':
    app.run()
