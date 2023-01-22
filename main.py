from flask import Flask, render_template, request
import spacy
#import ru_core_news_sm

app = Flask(__name__)
# spacy.cli.download("ru")
nlp = spacy.load('ru_core_news_sm')


@app.route('/')
def main_page():
    return render_template('index.html')


@app.route('/result', methods=['POST', 'GET'])
def result():
    if request.method == "GET":
        return render_template("index.html")

    user_request = request.form['text']
    print(user_request)

    # connection = sqlite3.connect('math_db_new_1.db')
    # cur = connection.cursor()

    return render_template('result.html')


if __name__ == '__main__':
    app.run()
