import re
from collections import namedtuple
from dataclasses import dataclass

from database import DBHandler


@dataclass
class QueryTokenInfo:
    token: str
    color: str = 'black'
    model: str = None


def create_query_info(user_request, spacy_lm):
    lemmas = []
    poses = []
    pic_files = []
    token_infos = []
    db = DBHandler('math_corpus_database.db')
    pics_list = db.get_math_pics()
    for t in spacy_lm(user_request):
        lemmas.append(t.lemma_)
        poses.append(t.pos_)
        token_info = QueryTokenInfo(token=t.text)
        math_info = db.get_math_info(t.lemma_)
        if math_info:
            features, model = math_info
            if model:
                token_info.model = model
            for tag, file in pics_list:
                if tag in features.split(';') and tag != 'number' and tag != 'var_any':
                    pic_files.append(file)
                    token_info.color = 'pink'
        token_infos.append(token_info)
    return token_infos, poses, lemmas, pic_files


def filter_selected_sentences(db_selected, user_request):
    """
    Отбирает из выбранных из бд предложений те, где между словами запроса не более 1 слова
    :param db_selected: список из лемматизированных предложений из бд
    :param user_request: список из лемматизированных строк запроса
    """

    reg_ex = '\s?([А-Яа-яёЁ]+)?\s?'.join(user_request)
    filtered = []
    for sent in db_selected:
        if re.search(reg_ex, sent.lemmatized):
            filtered.append(sent)
    return filtered


