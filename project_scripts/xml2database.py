# !pip install spacy
# !python -m spacy download ru_core_news_sm
# pip install beautifulsoup4

import pymorphy2
import spacy
import re
from bs4 import BeautifulSoup
from dataclasses import dataclass
from tqdm import tqdm
from pathlib import Path

from database import ParserDBHandler


@dataclass
class SegmentInfo:
    seg_text: str
    available_search_area: str
    parent_id: str
    prev_char_count: int = 0
    char_start: int = 0
    char_end: int = 0
    features: str = None
    govern_model: str = None
    sentence: str = None


class XML2Database:
    nlp = spacy.load("ru_core_news_sm")
    morph = pymorphy2.MorphAnalyzer(lang='ru')

    def __init__(self, xml_filepath, database_path, textname=None):

        self.filepath = Path(xml_filepath)
        with open(self.filepath, 'r', encoding='utf-8') as f:
            xml_file_text = f.read()
        self.bs_data = BeautifulSoup(xml_file_text, "xml")
        self.db = ParserDBHandler(database_path)
        self.textname = textname

        if not self.textname:
            self.textname = self.filepath.stem

        self.text_id = self.db.add_text(textname)

    @staticmethod
    def parse_sentence_info_(analysed_sent):
        parsed = {
            'tokens': [],
            'lemmas': [],
            'poses': [],
            'deprels': [],
            'head_id_in_sent': [],
            'full_sentence': analysed_sent.text,
        }
        first_word_in_sent = 0

        for t in analysed_sent:
            parsed['tokens'].append(t.text)
            parsed['deprels'].append(t.dep_.lower())

            pos, lemma = XML2Database.specify_gram_annot(t)
            parsed['lemmas'].append(lemma)
            parsed['poses'].append(pos)

            if t.is_sent_start:
                first_word_in_sent = t.i
            parsed['head_id_in_sent'].append(t.head.i - first_word_in_sent)

        parsed['lemmatized_sent'] = ' '.join(parsed['lemmas'])
        return parsed

    @staticmethod
    def specify_gram_annot(spacy_token):
        if spacy_token.pos_ != 'VERB':
            return spacy_token.pos_, spacy_token.lemma_
        else:
            pymorphy_parsed = XML2Database.morph.parse(spacy_token.text)[0]
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
    def accum_token_info_(parsed, sent_id):
        n_tokens = len(parsed['tokens'])
        token_info = []
        sent_string = parsed['full_sentence']
        prev_chars_count = 0
        for i in range(n_tokens):
            token = parsed['tokens'][i]
            m = re.search(re.escape(token), sent_string)
            char_start, char_end = m.start(), m.end()

            token_info.append(
                (sent_id, i, parsed['tokens'][i], prev_chars_count + char_start, prev_chars_count + char_end))
            prev_chars_count += char_end
            sent_string = sent_string[char_end:]  # обрезаем строку, чтобы короткие слова не искались в начале строки
        return token_info

    @staticmethod
    def accum_grammar_info_(parsed, added_tokens):
        n_tokens = len(parsed['tokens'])
        head_ids = [added_tokens[hi] for hi in parsed['head_id_in_sent']]
        token_grammar_info = [
            (
                added_tokens[i],
                parsed['poses'][i],
                parsed['deprels'][i],
                head_ids[i],
                parsed['lemmas'][i]
            ) for i in range(n_tokens)
        ]
        return token_grammar_info

    def extract_sentences(self):
        full_text = self.bs_data.find('body').get_text().strip()
        sent_count = 0
        for sent in tqdm(list(self.nlp(full_text).sents)):
            sent_count += 1
            parsed_sentence = XML2Database.parse_sentence_info_(sent)

            lemmas = parsed_sentence['lemmas']
            added_lemmas = self.db.add_lemmas(lemmas)

            sent_text = parsed_sentence['full_sentence']
            sent_lemmatized = parsed_sentence['lemmatized_sent']
            sent_id = self.db.add_sent(self.text_id, sent_text, sent_lemmatized, sent_count)

            tokens_info = XML2Database.accum_token_info_(parsed_sentence, sent_id)
            added_tokens = self.db.add_tokens(tokens_info)

            grammar_info = XML2Database.accum_grammar_info_(parsed_sentence, added_tokens)
            self.db.add_grammar_annot(grammar_info)
        self.db.change_text_status(self.text_id, 2)

    #         print('all sentences added to dabase')

    @staticmethod
    def parse_annotation_segments_(bs_data):
        segments = {}
        for s in bs_data.find('body').find_all('segment', recursive=True):
            parent_id = s.parent.get('id')
            segments[s.get('id')] = SegmentInfo(s.get_text().strip(), s.get_text().strip(), parent_id)
        for seg_id in segments:
            segment_xml = bs_data.find('segment', {'id': seg_id})
            parent_id = segments[seg_id].parent_id

            if not parent_id:  # то есть, что это сегмент с предложением
                segments[seg_id].sentence = segments[seg_id].seg_text
            else:

                search_area = segments[parent_id].available_search_area
                m = re.search('(?<![A-я])' + re.escape(segments[seg_id].seg_text) + '(?![A-я])', search_area)
                start, end = m.start(), m.end()
                segments[seg_id].char_start = segments[parent_id].char_start + segments[
                    parent_id].prev_char_count + start
                segments[seg_id].char_end = segments[parent_id].char_start + segments[parent_id].prev_char_count + end
                segments[seg_id].sentence = segments[parent_id].sentence

                if segment_xml.get('features'):
                    segments[seg_id].features = segment_xml.get('features')
                if segment_xml.get('comment'):
                    segments[seg_id].govern_model = segment_xml.get('comment')

                segments[parent_id].available_search_area = segments[parent_id].available_search_area[end:]
                segments[parent_id].prev_char_count += m.end()
        return segments

    def extract_math_annotation(self):
        annot_segments = []
        segments = XML2Database.parse_annotation_segments_(self.bs_data)
        for seg_id in tqdm(segments):
            if segments[seg_id].features:
                sentences = list(self.nlp(segments[seg_id].sentence).sents)
                sentences_starts = [s.start_char for s in sentences]
                segment_sent = sentences_starts.index(
                    [s for s in sentences_starts if s <= segments[seg_id].char_start][-1])
                new_char_end = segments[seg_id].char_end - sentences_starts[segment_sent]
                new_char_start = segments[seg_id].char_start - sentences_starts[segment_sent]
                annot_segments.append({
                    'sentence': sentences[segment_sent].text,
                    'segment_text': segments[seg_id].seg_text,
                    'char_start': new_char_start,
                    'char_end': new_char_end,
                    'annot': segments[seg_id].features,
                    'govern_model': segments[seg_id].govern_model
                })
                # bolded_print(sentences[segment_sent].text, (new_char_start, new_char_end))
        self.db.add_math_annotation(annot_segments)
        print('all math annotation added to database')
