import re


def parse_request(user_request, spacy_lm):
    """

    :param user_request:
    :param spacy_lm:
    :return:
    """
    token_lemma_pos = [(t.text, t.lemma_, t.pos_)for t in spacy_lm(user_request)]
    return token_lemma_pos

def filter_selected_sentences(db_selected, user_request):
    """
    Отбирает из выбранных из бд предложений те, где между словами запроса не более 1 слова
    :param db_selected: список из лемматизированных предложений из бд
    :param user_request: список из лемматизированных строк запроса
    """
    
    reg_ex = '\s?([А-Яа-яёЁ]+)?\s?'.join(user_request)
    filtered = []
    for sent in db_selected:
        if re.search(reg_ex, sent):
            filtered.append(sent)
    return filtered