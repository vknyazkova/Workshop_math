from flask import Flask, render_template, request, redirect, url_for
import spacy
from pathlib import Path
from collections import namedtuple

from backend.utils import filter_selected_sentences, create_query_info, create_sentences_info, create_full_link
from backend.database import WebDBHandler


app = Flask(__name__)
nlp = spacy.load('ru_core_news_sm')
DB_PATH = Path('./math_corpus_database.db').resolve()


@app.route('/')
def main_page():
    return redirect(url_for('main_page_r', lang = "en"))


@app.route('/main_<lang>')
def main_page_r(lang):
    return render_template('home.html', stat1="disabled", main_lan=lang)


@app.route('/about_<lang>')
def about_page_r(lang):
    return render_template('base.html', stat2="disabled", main_lan=lang)


@app.route('/dictionary_<lang>')
def dict_page_r(lang):
    return render_template('base.html', stat3="disabled", main_lan=lang)


@app.route('/check_<lang>')
def check_page_r(lang):
    return render_template('base.html', stat4="disabled", main_lan=lang)


@app.route('/login_<lang>', methods=['POST', 'GET'])
def login_r(lang):
    return render_template('login.html', stat5="disabled", main_lan=lang)


@app.route('/register_<lang>')
def reg_page_r(lang):
    return render_template('registration.html', stat6="disabled", main_lan=lang)


@app.route('/result_<query>_<lang>', methods=['POST', 'GET'])
def result_with_query(query, lang):
    query_info = create_query_info(query, nlp, DB_PATH)

    db = WebDBHandler(DB_PATH)

    selected_sentences = db.select_sentences(query_info.lemmatized.split(' '))
    SentenceInfo = namedtuple('SentenceInfo', ['id', 'sent', 'lemmatized', 'link'])
    selected_sentences = [SentenceInfo(s[0], s[1], s[2], create_full_link(s[3], s[4])) for s in selected_sentences]
    matching_sentences = filter_selected_sentences(selected_sentences, query_info.lemmatized.split(' '))

    sents_info = create_sentences_info(matching_sentences, query_info, DB_PATH)

    # print(query_info)
    # print(sents_info)

    return render_template('result.html', main_lan=lang, query_info=query_info, sents_info=sents_info)


@app.route('/result_<lang>', methods=['POST', 'GET'])
def result(lang):
    user_request = request.form['text']
    if user_request == "":
        return render_template('home.html', stat1="disabled", main_lan=lang)
    return redirect(url_for('result_with_query', query = user_request, lang = lang))


if __name__ == '__main__':
    app.run()
