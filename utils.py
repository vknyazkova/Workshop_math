import re
from dataclasses import dataclass
from translate import Translator
from typing import Iterable
from database import DBHandler


@dataclass
class TokenInfo:
    token: str
    color: str


@dataclass
class ResultTokenInfo:
    color: str = 'black'
    pos: str = None
    lemma: str = None


@dataclass
class QueryTokenInfo(TokenInfo):
    color: str = 'green'
    model: str = None


@dataclass
class QueryInfo:
    text: str
    tokens: Iterable[QueryTokenInfo] = None
    translation: str = None
    pos_string: str = None
    lemmatized: str = None
    pictures: list = None


def create_query_info(user_request, spacy_lm, db_path) -> QueryInfo:
    """
    Парсит запрос, переводит и возвращает всю информацию в виде экземпляра датакласса QueryInfo
    """

    query_info = QueryInfo(user_request)
    translator = Translator(to_lang="en", from_lang='ru')
    query_info.translation = translator.translate(user_request)

    query_info.tokens = []
    query_info.pictures = []

    lemmas = []
    poses = []

    db = DBHandler(db_path)
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
            if features:
                for tag, file in pics_list:
                    if tag in features.split(';') and tag != 'number' and tag != 'var_any':
                        query_info.pictures.append(file)
                        token_info.color = 'pink'
        query_info.tokens.append(token_info)
    query_info.lemmatized = ' '.join(lemmas)
    query_info.pos_string = ' '.join(poses)
    return query_info


def filter_selected_sentences(db_selected, user_request) -> Iterable[tuple]:
    """
    Отбирает из выбранных из бд предложений те, где между словами запроса не более 1 слова
    :param db_selected: список из namedtuple(id, sent, lemmatized)
    :param user_request: список из лемматизированных строк запроса
    """

    reg_ex = '\s?([А-Яа-яёЁ]+)?\s?'.join(user_request)
    filtered = []
    for sent in db_selected:
        if re.search(reg_ex, sent.lemmatized):
            filtered.append(sent)
    return filtered


def create_sentences_info(matching_sentences, query_info, db_path) -> Iterable[Iterable[ResultTokenInfo]]:
    """
    Возращает список со списком TokenInfo для каждого предложения
    TokenInfo - датакласс с полями: token, color, pos, lemma
    """
    sentences = []
    query_lemmas_with_colors = {l: query_info.tokens[i].color for i, l in enumerate(query_info.lemmatized.split(' '))}
    db = DBHandler(db_path)
    for sent in matching_sentences:
        sent_info = []
        sent_annot = db.get_grammar_annotation(sent.id)
        for i, token_annot in enumerate(sent_annot):
            if token_annot[1] == 'PUNCT':
                continue
            else:
                token_info = ResultTokenInfo(token_annot[0], pos=token_annot[1], lemma=token_annot[2])
                if i + 1 < len(sent_annot):
                    if sent_annot[i + 1][1] == 'PUNCT':
                        token_info.token = token_annot[0] + sent_annot[i + 1][0]
                        token_info.lemma = token_annot[2] + sent_annot[i + 1][2]
                if token_annot[2] in query_lemmas_with_colors:
                    token_info.color = query_lemmas_with_colors[token_annot[2]]
            sent_info.append(token_info)
        sentences.append(sent_info)

    return sentences

