import sqlite3


class ParserDBHandler:
    conn = None
    cur = None

    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cur = self.conn.cursor()

    def __del__(self):
        self.conn.close()

    def add_text(self, text_name):

        self.cur.execute('''INSERT or IGNORE INTO texts (name)
                            VALUES (?)
                            RETURNING id''', (text_name,))

        added_id = self.cur.fetchone()
        self.conn.commit()

        if not added_id:
            self.cur.execute('''SELECT id
                                FROM texts
                                WHERE name = (?)''', (text_name,))
            added_id = self.cur.fetchone()
        return added_id[0]

    def add_sent(self, text_id, sent, lemmatized, sent_count):

        self.cur.execute('''INSERT INTO sents (text_id, sent, lemmatized, pos_in_text)
                            VALUES (?, ?, ?, ?)
                            RETURNING id''', (text_id, sent, lemmatized, sent_count))

        added_id = self.cur.fetchone()
        self.conn.commit()
        return added_id[0]

    def add_tokens(self, tokens_info):
        ":param tokens_info: list of tuples (sent_id, word_in_sent, token, char_start, char_end)"

        self.cur.executemany('''INSERT INTO tokens (sent_id, word_in_sent, token, char_start, char_end)
                                VALUES (?, ?, ?, ?, ?)''', tokens_info)

        self.conn.commit()

        self.cur.execute('''SELECT id 
                            FROM tokens
                            WHERE sent_id = (?)
                            ORDER BY word_in_sent''', (tokens_info[0][0],))
        added_ids = self.cur.fetchall()
        return [token_id[0] for token_id in added_ids]

    def add_lemmas(self, lemmas):
        lemmas = [(el,) for el in lemmas]
        self.cur.executemany('''INSERT or IGNORE
                            INTO lemmas (name)
                            VALUES (?)''', lemmas)
        self.conn.commit()

        lemma_ids = []
        for lemma in lemmas:
            self.cur.execute('''SELECT id
                                FROM lemmas
                                WHERE name = ?''', lemma)
            lemma_ids.append(self.cur.fetchone()[0])
        return lemma_ids

    def add_grammar_annot(self, token_grammar_info):
        ":param token_grammar_info: [(token_id, pos, deprel, head_id, lemma)]"

        self.cur.executemany('''INSERT INTO grammar_annotation (token_id, lemma_id, pos_id, deprel_id, head_id)
                                SELECT ?, 
                                        lemmas.id, 
                                        (SELECT pos.id FROM pos WHERE pos.name = ?),
                                        (SELECT deprels.id FROM deprels WHERE deprels.name = ?),
                                        ?
                                FROM lemmas
                                WHERE lemmas.name = ?''', token_grammar_info)
        self.conn.commit()

    def add_math_tags(self, tags):
        tags = [(el,) for el in tags]
        self.cur.executemany('''INSERT or IGNORE
                                INTO math_tags (feature)
                                VALUES (?)''', tags)
        self.conn.commit()

    def add_govern_models(self, models):
        models = [(el,) for el in models]
        self.cur.executemany('''INSERT or IGNORE
                                INTO govern_models (model)
                                VALUES (?)''', models)
        self.conn.commit()

    def get_sent_id(self, sentence):
        self.cur.execute('''SELECT id
                            FROM sents
                            WHERE sents.sent = (?)''', (sentence,))
        #         print(sentence)
        return self.cur.fetchone()[0]

    def add_math_annotation(self, annotation):
        """:param annotation: [{
            'sentence': str,
            'segment_text': str,
            'char_start': int,
            'char_end': int,
            'annot': str,
            'govern_model': str}
            }]"""

        annot = list(set([an['annot'] for an in annotation]))
        self.add_math_tags(annot)
        govern_models = list(set([an['govern_model'] for an in annotation if an['govern_model']]))
        self.add_govern_models(govern_models)

        sent_ids = {}
        for annot in annotation:
            if not sent_ids.get(annot['sentence']):
                sent_ids[annot['sentence']] = self.get_sent_id(annot['sentence'])
            annot['sentence_id'] = sent_ids[annot['sentence']]

        self.cur.executemany('''INSERT INTO math_annotation (feature_id, govern_model_id, id_token_start, id_token_end)
                                SELECT math_tags.id, 
                                (SELECT govern_models.id FROM govern_models WHERE govern_models.model = :govern_model),
                                (SELECT tokens.id FROM tokens 
                                WHERE tokens.char_start >= :char_start AND tokens.char_end <= :char_end AND tokens.sent_id = :sentence_id
                                ORDER BY tokens.word_in_sent 
                                LIMIT 1),
                                (SELECT tokens.id FROM tokens 
                                WHERE tokens.char_start >= :char_start AND tokens.char_end <= :char_end AND tokens.sent_id = :sentence_id
                                ORDER BY tokens.word_in_sent DESC
                                LIMIT 1)
                            FROM math_tags
                            WHERE math_tags.feature = :annot''', annotation)
        self.conn.commit()

    def change_text_status(self, text_id, new_status):
        self.cur.execute('''UPDATE texts
                            SET status_id = (?)
                            WHERE id = (?)''', (new_status, text_id))
        self.conn.commit()
        
    def add_youtube_link(self, text_id, link):
        self.cur.execute('''UPDATE texts
                            SET youtube_link = (?)
                            WHERE id = (?)''', (link, text_id))
        self.conn.commit()