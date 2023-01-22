from flask import Flask, render_template, request
import spacy
import os.path
from translate import Translator
from pprint import pprint
from dataclasses import dataclass
#import ru_core_news_sm
from utils import filter_selected_sentences, create_query_info
from database import DBHandler


app = Flask(__name__)
# spacy.cli.download("ru")
nlp = spacy.load('ru_core_news_sm')
DB_PATH = 'math_corpus_database.db'


@app.route('/')
def main_page():
    return render_template('index.html')


@app.route('/result', methods=['POST', 'GET'])
def result():
    if request.method == "GET":
        return render_template("index.html")

    user_request = request.form['text']
    # parsed_ur = parse_request(user_request, nlp)
    query_info, query_pos, query_lemma, pictures = create_query_info(user_request, nlp)
    db = DBHandler(os.path.abspath(DB_PATH))

    selected_sentences = db.select_sentences(query_lemma)
    matching_sentences = filter_selected_sentences(selected_sentences, query_lemma)

    translator = Translator(to_lang="en", from_lang='ru')
    translation = translator.translate(user_request)

    pprint(query_info)
    print(' '.join(query_pos))
    print(' '.join(query_lemma))
    print(pictures)
    pprint(matching_sentences)
    print(translation)

    return None
    # return render_template('result.html')


if __name__ == '__main__':
    app.run()
