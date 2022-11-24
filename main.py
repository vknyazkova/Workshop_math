
from flask import (
    Flask, jsonify, render_template, request, redirect, sessions, url_for
)
import json
import sqlite3
import pandas
from pandas import DataFrame
from googletrans import Translator
from translate import Translator
import pyttsx3
from pymystem3 import Mystem
m = Mystem()
from conllu import parse
import pandas as pd
import re
from natasha import (
    Segmenter,
    MorphVocab,

    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    NewsNERTagger,

    PER,
    NamesExtractor,

    Doc
)
segmenter = Segmenter()



app = Flask(__name__)
engine = pyttsx3.init()


@app.route('/')
def main_page():
    return render_template('index.html')



def find_indices(list_to_check, item_to_find):
    return [idx for idx, value in enumerate(list_to_check) if value == item_to_find]


def find_word_indexes(sent_l, lem_var, dist=2):
    i = 0
    j = 0
    li_ind = []
    result_li = []
    while i < len(sent_l):
        if sent_l[i] == lem_var[j]:
            li_ind.append(i)

            j += 1
            i += 1

            if j >= len(lem_var):
                result_li.append(li_ind)
                li_ind = []
                j = 0
        else:
            i += 1
            if len(li_ind) >= 1:
                if i - li_ind[-1] > dist:
                    j = 0
                    li_ind = []
                    continue
    return result_li


@app.route('/result.html', methods=['POST', 'GET'])
def result():
    if request.method == "GET":
        return render_template("index.html")

    my_var = request.form['text']

    connection = sqlite3.connect('math_db_new_1.db')
    cur = connection.cursor()

    #select matching sents
    text = my_var

    doc = Doc(text)
    doc.segment(segmenter)
    morph_vocab = MorphVocab()
    emb = NewsEmbedding()
    morph_tagger = NewsMorphTagger(emb)

    doc.tag_morph(morph_tagger)

    for token in doc.tokens:
        token.lemmatize(morph_vocab)

    my_var_lemm = [_.lemma for _ in doc.tokens]
    my_var_lemm_mystem = m.lemmatize(text)
    my_var_lemm_mystem = ''.join(my_var_lemm_mystem).split('\n')[0]
    my_var_lemm = ' '.join(my_var_lemm).split('\n')[0]

    li_word_pos = []
    for el in doc.tokens:
        li_word_pos.append(el.pos)


    var_for_sent = [elem for elem in my_var_lemm_mystem.split(' ')]
    var_for_sent = '%'+'%'.join(var_for_sent)+'%'

    query = f'select id, sent.sent, sent.sent_lemmatized from sent where sent.sent_lemmatized like "{var_for_sent}"'

    li_ans = cur.execute(query)

    df = DataFrame(li_ans.fetchall())

    pos_query = 'select conllu_labels.id_sent, conllu_labels.token, pos.pos,sent.sent, sent.sent_lemmatized from conllu_labels ' \
    'join sent on conllu_labels.id_sent = sent.id ' \
    'join pos on conllu_labels.pos_id = pos.id ' \
    f'where sent.sent_lemmatized like "{var_for_sent}" '

    li_pos = cur.execute(pos_query)
    df_pos = DataFrame(li_pos.fetchall())
    li_pos = list(zip(df_pos[0], df_pos[2]))

    result = {}
    for i in li_pos:
        result.setdefault(i[0], []).append(i[1])
    poses = []
    for v in result.values():
        poses.append(v)

    #postprocess sents
    reg_q = ''
    lem_var = my_var_lemm_mystem.split(' ')
    for i in range(len(lem_var)):
        if i < len(lem_var)-1:
            reg_q += f'{lem_var[i]}\s?([А-Яа-яёЁ]+)?\s?'
        else:
            reg_q += f'{lem_var[i]}'


    if df.empty:
        df_postproc = ''
    else:
        df_postproc = df[df[2].str.contains(reg_q, regex=True)]


    #translate to english
    translator = Translator(to_lang="en", from_lang='ru')
    translation = translator.translate(my_var)

    #translate to pic
    df_pics = pd.read_csv('static/pics/Tags_filenames.csv')
    lemmas_li = []

    for elem in my_var_lemm.split(' '):
        query = f'select token, features, model from math_labels ' \
                'where lower(math_labels.token) = lower(' \
                '(select token from conllu_labels where lemma_id = ' \
                f'(select id from lemma where lemma = "{elem}") limit 1)) limit 1'

        li_elems = cur.execute(query)

        lemmas_li.append(li_elems.fetchone())


    for i in range(len(lemmas_li)):
        if elem == None:
            lemmas_li.remove(lemmas_li[i])

    model = [feat[2] for feat in lemmas_li if feat != None]
    model = [el for el in model if el != '']
    if len(model) > 0:
        model = model[0]
    else:
        model = ''
    features = [feat[1] for feat in lemmas_li if feat != None]
    indexes_none = [i for i in range(len(lemmas_li)) if lemmas_li[i] == None]

    li_tags = df_pics['Tag'].tolist()
    li_pics = df_pics['Filename'].tolist()

    features = [feat.split(';') for feat in features]

    flat_list = [item for sublist in features for item in sublist]
    index_li = []
    for el in flat_list:
        if el in li_tags:
            index_pic = li_tags.index(el)
            index_li.append(index_pic)
    files = []
    root_words = []
    var_nums = []

    item_list = [lem_var[i] for i in range(len(lem_var)) if i not in indexes_none]

    if len(index_li) > 0:
        for i, id in enumerate(index_li):
            if li_pics[id]:
                if li_pics[id] != 'number.png' and li_pics[id] != 'var.png':
                    files.append(li_pics[id])
                    root_words.append(item_list[i])
            else:
                var_nums.append(item_list[i])

    connection.commit()
    connection.close()

    # check if df is not []
    if len(df) == 0:
        return render_template("result.html", word=my_var,
                               trans=translation, files = files)
    #make html table from df
    df.drop_duplicates(inplace=True)
    column_names = df.columns.values
    if type(df_postproc) is str:
        sent_data = ''
    else:
        sent_data = list(df[1].values.tolist())
        sent_lem_data = list(df[2].values.tolist())


    di_inst = {}
    for i, sent_l in enumerate(sent_lem_data):
        new_li = []
        words_indexes= find_word_indexes(sent_l.strip().split(' '), lem_var)
        if len(words_indexes) != 0:
            di_inst[i] = words_indexes

    return render_template("result.html", word=my_var, column_names = column_names, row_data=sent_data, lemmatized_sents =  sent_lem_data,  trans=translation, files = files, root_words = root_words, var_nums = var_nums, indexes= di_inst, re = re, poses = poses, model = model, word_l = my_var_lemm_mystem, pos_l = ' '.join(li_word_pos))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=60)

