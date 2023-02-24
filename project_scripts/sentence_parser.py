# !pip install spacy
# !python -m spacy download ru_core_news_sm

import pymorphy2
import spacy
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Iterable
import re
from tqdm import tqdm

from database import ParserDBHandler


@dataclass
class ParsedSentence:
    full_sentence: str
    lemmatized_sent: str = None
    tokens: List[str] = field(default_factory=list)
    lemmas: List[str] = field(default_factory=list)
    poses: List[str] = field(default_factory=list)
    deprels: List[str] = field(default_factory=list)
    head_id_in_sent: List[int] = field(default_factory=list)


class Text2DB:
    nlp = spacy.load("ru_core_news_sm")
    morph = pymorphy2.MorphAnalyzer(lang='ru')

    def __init__(self, filepath, database_path, textname=None):

        self.filepath = Path(filepath)
        self.db = ParserDBHandler(database_path)
        self.textname = textname

        if not self.textname:
            self.textname = filepath.stem
        self.text = None
        self.text_id = self.db.add_text(self.textname)

    def read(self):
        with open(self.filepath, 'r', encoding='utf-8-sig') as f:
            self.text = ''
            for line in f.readlines():
                self.text += line.strip()

    @staticmethod
    def specify_gram_annot(spacy_token):
        if spacy_token.pos_ != 'VERB':
            return spacy_token.pos_, spacy_token.lemma_
        else:
            pymorphy_parsed = Text2DB.morph.parse(spacy_token.text)[0]
            if pymorphy_parsed.tag.POS == 'VERB':
                return spacy_token.pos_, spacy_token.lemma_
            elif pymorphy_parsed.tag.POS == 'GRND':
                return 'GRD (VERB)', spacy_token.lemma_
            elif pymorphy_parsed.tag.POS in ['PRTF', 'PRTS']:
                pos = 'PTCP (VERB)'
                norm_from = pymorphy_parsed.inflect({'sing', 'masc', 'nomn'}).word
                return pos, norm_from + ' (' + spacy_token.lemma_ + ')'
            else:
                return spacy_token.pos_, spacy_token.lemma_

    @staticmethod
    def parse_sentence_info_(analysed_sent: spacy.tokens.doc.Doc) -> ParsedSentence:
        parsed = ParsedSentence(analysed_sent.text)
        first_word_in_sent = 0

        for t in analysed_sent:
            parsed.tokens.append(t.text)
            parsed.deprels.append(t.dep_.lower())

            pos, lemma = Text2DB.specify_gram_annot(t)
            parsed.lemmas.append(lemma)
            parsed.poses.append(pos)

            if t.is_sent_start:
                first_word_in_sent = t.i  # тк вся индексация с начала предложени
            parsed.head_id_in_sent.append(t.head.i - first_word_in_sent)

        parsed.lemmatized_sent = ' '.join(parsed.lemmas)
        return parsed

    @staticmethod
    def accum_token_info_(parsed: ParsedSentence, sent_id: int) -> List[tuple]:
        n_tokens = len(parsed.tokens)
        token_info = []
        sent_string = parsed.full_sentence
        prev_chars_count = 0
        for i in range(n_tokens):
            token = parsed.tokens[i]
            m = re.search(re.escape(token), sent_string)
            char_start, char_end = m.start(), m.end()

            token_info.append(
                (sent_id, i, parsed.tokens[i], prev_chars_count + char_start, prev_chars_count + char_end))
            prev_chars_count += char_end
            sent_string = sent_string[char_end:]  # обрезаем строку, чтобы короткие слова не искались в начале строки
        return token_info

    @staticmethod
    def accum_grammar_info_(parsed: ParsedSentence, added_tokens: Iterable[int]):
        n_tokens = len(parsed.tokens)
        head_ids = [added_tokens[hi] for hi in parsed.head_id_in_sent]
        token_grammar_info = [
            (
                added_tokens[i],
                parsed.poses[i],
                parsed.deprels[i],
                head_ids[i],
                parsed.lemmas[i]
            ) for i in range(n_tokens)
        ]
        return token_grammar_info

    def extract_sentences(self):
        if not self.text:
            self.read()

        sent_count = 0
        for sent in tqdm(list(self.nlp(self.text).sents)):
            sent_count += 1
            parsed_sentence = Text2DB.parse_sentence_info_(sent)

            lemmas = parsed_sentence.lemmas
            added_lemmas = self.db.add_lemmas(lemmas)

            sent_text = parsed_sentence.full_sentence
            sent_lemmatized = parsed_sentence.lemmatized_sent
            sent_id = self.db.add_sent(self.text_id, sent_text, sent_lemmatized, sent_count)

            tokens_info = Text2DB.accum_token_info_(parsed_sentence, sent_id)
            added_tokens = self.db.add_tokens(tokens_info)

            grammar_info = Text2DB.accum_grammar_info_(parsed_sentence, added_tokens)
            self.db.add_grammar_annot(grammar_info)
        self.db.change_text_status(self.text_id, 2)
