import flask
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from pathlib import Path
from collections import namedtuple
from sqlite3 import IntegrityError

import spacy

from backend.utils import filter_selected_sentences, create_query_info, create_sentences_info, create_full_link
from backend.database import WebDBHandler
from user import User
from secret import FLASK_SECRET_KEY


app = Flask(__name__)
app.config['SECRET_KEY'] = FLASK_SECRET_KEY

login_manager = LoginManager(app)
login_manager.init_app(app)

nlp = spacy.load('ru_core_news_sm')
DB_PATH = Path('./math_corpus_database.db').resolve()


@login_manager.user_loader
def load_user(user_id):
    return User(DB_PATH).get(user_id)


@app.route('/')
def start_page():
    return redirect(url_for('main_page', lang="en"))


@app.route('/main_<lang>')
def main_page(lang):
    return render_template('home.html', main_lan=lang)


@app.route('/result_<lang>', methods=['POST', 'GET'])
def result(lang):
    # временный костыль лишь бы работали кнопки
    if request.form['type'] == "By text":
        user_request = request.form['query']
    else:
        user_request = "вы ввели формулу"
    return redirect(url_for('result_page', lang=lang, query=user_request))


@app.route('/<query>_<lang>')
def result_page(query, lang, ):
    query_info = create_query_info(query, nlp, DB_PATH)
    db = WebDBHandler(DB_PATH)

    selected_sentences = db.select_sentences(query_info.lemmatized.split(' '))
    # print(selected_sentences)
    SentenceInfo = namedtuple('SentenceInfo', ['id', 'sent', 'lemmatized', 'link'])
    selected_sentences = [SentenceInfo(s[0], s[1], s[2], create_full_link(s[3], s[4])) for s in selected_sentences]
    matching_sentences = filter_selected_sentences(selected_sentences, query_info.lemmatized.split(' '))
    sents_info = create_sentences_info(matching_sentences, query_info, DB_PATH)


    # print(query_info.pictures)
    # print(sents_info)

    return render_template('result.html', main_lan=lang, query_info=query_info, sents_info=sents_info, query=query)


@app.route('/dictionary_<lang>')
def dict_page(lang):
    return render_template('dictionary.html', main_lan=lang)


@app.route('/check_<lang>')
def check_page(lang):
    return render_template('base.html', main_lan=lang)


@app.route('/account_<lang>', methods=['POST', 'GET'])
def account(lang):
    if not current_user.is_authenticated:
        return redirect(url_for('login', lang=lang))
    else:
        return render_template('account.html', main_lan=lang, login=current_user.username, email=current_user.email)


@app.route('/login_<lang>', methods=['GET', 'POST'])
def login(lang):
    if request.method == 'POST':
        un = request.form['username']
        user = User(DB_PATH).get(un)
        if user:
            if user.validate_password(request.form['password']):
                login_user(user, remember=True)
                flask.flash(f'You\'ve been successfully logged-in')
                return redirect(url_for('account', lang=lang))
    return render_template('login.html', main_lan=lang)


@app.route("/logout_<lang>")
@login_required
def logout(lang):
    logout_user()
    return redirect(flask.url_for('main_page', lang=lang))


@app.route('/register_<lang>', methods=['GET', 'POST'])
def reg_page(lang):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        hashed_password, salt = User.hash_password(password)
        db = WebDBHandler(DB_PATH)
        try:
            db.add_user(username, hashed_password, salt, email)
            flask.flash('You\'ve been successfully logged-in')
            user = User(DB_PATH).get(username)
            login_user(user, remember=True)
            return render_template('account.html', main_lan=lang, login=current_user.username, email=current_user.email)

        except IntegrityError as e:  # если такой юзер уже есть в бд
            dupl_field = str(e).split()[-1].split('.')[-1]
            flask.flash(f'The user with this {dupl_field} already exists')
            return redirect(flask.url_for('reg_page', lang=lang))
    return render_template('register.html', main_lan=lang)


@app.route('/help_<lang>')
def help(lang):
    db = WebDBHandler(DB_PATH)
    poses = db.get_pos_tags()
    example_email = "mathematicon@gmail.com"
    example_tg_account = "@mathematicon"
    return render_template('help.html', main_lan=lang, POS_tags=poses, example_email=example_email, example_tg_account=example_tg_account)


@app.route('/reset_<lang>')
def reset(lang):
    return render_template('base.html', main_lan=lang)


if __name__ == '__main__':
    app.run()
