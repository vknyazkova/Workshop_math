from flask import Flask, render_template, request
import spacy
import os.path
#import ru_core_news_sm
from utils import parse_request, filter_selected_sentences
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
    parsed_ur = parse_request(user_request, nlp)

    db = DBHandler(os.path.abspath(DB_PATH))
    lemmatized_ur = [t.lemma for t in parsed_ur]
    selected_sentences = db.select_sentences(lemmatized_ur)
    matching_sentences = filter_selected_sentences(selected_sentences, lemmatized_ur)
    print(matching_sentences)
    pass
    return render_template('result.html')


if __name__ == '__main__':
    app.run()
