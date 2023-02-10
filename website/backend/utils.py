import re
from translate import Translator
from typing import Iterable
from website.backend.database import WebDBHandler

from website.backend.custom_dataclasses import ResultInfo, ResultTokenInfo, QueryInfo, QueryTokenInfo


def create_query_info(user_request: str, spacy_lm, db_path: str) -> QueryInfo:
    """Парсит запрос, переводит и возвращает всю информацию в виде экземпляра датакласса QueryInfo"""

    query_info = QueryInfo(user_request)
    translator = Translator(to_lang="en", from_lang='ru')
    query_info.translation = translator.translate(user_request)

    query_info.tokens = []
    query_info.pictures = []

    lemmas = []
    poses = []

    db = WebDBHandler(db_path)
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
    :param db_selected: список из namedtuple(id, sent, lemmatized, link)
    :param user_request: список из лемматизированных строк запроса
    """

    reg_ex = '\s?([А-Яа-яёЁ]+)?\s?'.join(user_request)
    filtered = []
    for sent in db_selected:
        if re.search(reg_ex, sent.lemmatized):
            filtered.append(sent)
    return filtered


def create_sentences_info(matching_sentences, query_info: QueryInfo, db_path) -> Iterable[ResultInfo]:
    """Возращает список с нужной информацией о каждом предложении из выдачи в виде экземпляра датакласса ResultInfo"""

    sentences = []
    query_lemmas_with_colors = {l: query_info.tokens[i].color for i, l in enumerate(query_info.lemmatized.split(' '))}
    db = WebDBHandler(db_path)

    for sent in matching_sentences:
        sent_info = ResultInfo(youtube_link=sent.link)
        sent_info.tokens = []
        sent_annot = db.get_grammar_annotation(sent.id)
        for i, token_annot in enumerate(sent_annot):
            if token_annot[1] == 'PUNCT':
                continue
            else:
                token_info = ResultTokenInfo(token=token_annot[0], pos=token_annot[1], lemma=token_annot[2])
                if i + 1 < len(sent_annot):
                    if sent_annot[i + 1][1] == 'PUNCT':  # приклеиваем запятые к словам
                        token_info.token = token_annot[0] + sent_annot[i + 1][0]
                        token_info.lemma = token_annot[2] + sent_annot[i + 1][2]
                if token_annot[2] in query_lemmas_with_colors:
                    if token_within_query(query_info.lemmatized, sent.lemmatized, i):
                        token_info.color = query_lemmas_with_colors[token_annot[2]]
            sent_info.tokens.append(token_info)
        sentences.append(sent_info)

    return sentences


def create_full_link(video_link, timecode):
    """Собирает ссылку на определенный момент в видео"""

    if video_link and timecode:
        start = timecode.split(' ')[0]
        return video_link + '&t=' + start + 's'
    return


def token_within_query(query_lemmatized: str, sentence_lemmatized: str, i) -> bool:
    """
    Проверяет, что i-е слово стоит рядом со словами из запроса, а не отдельно в предложении
    :param query_lemmatized: строка лемматизированного запроса
    :param sentence_lemmatized: строка лемматизированного предложения
    :param i: порядковый номер в предложении токена, который мы проверяем
    """

    query_lemmatized_list = query_lemmatized.split(' ')
    sentence_lemmatized_list = sentence_lemmatized.split(' ')

    i_token_char_start = len(' '.join(sentence_lemmatized_list[: i])) + 1
    i_token_char_end = i_token_char_start + len(sentence_lemmatized_list[i])

    reg_ex = '\s?([А-Яа-яёЁ]+)?\s?'.join(query_lemmatized_list)
    for m in re.finditer(reg_ex, sentence_lemmatized):
        if i_token_char_start >= m.start() and i_token_char_end <= m.end():
            return True
    return False
