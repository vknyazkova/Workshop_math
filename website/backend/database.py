import sqlite3


class WebDBHandler:
    conn = None
    cur = None

    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cur = self.conn.cursor()

    def __del__(self):
        self.conn.close()

    def select_sentences(self, lemmatized_request):
        pattern = '%' + '%'.join(lemmatized_request) + '%'
        self.cur.execute('''SELECT sents.id, sents.sent, sents.lemmatized, texts.youtube_link, sents.timecode
                            FROM sents
                            LEFT JOIN texts
                                ON texts.id = sents.text_id
                            WHERE sents.lemmatized LIKE ?''', (pattern,))
        return self.cur.fetchall()

    def get_math_info(self, lemma):
        """TO DO:
        Исправить полностью эту функцию"""
        lemma = lemma.lower()
        self.cur.execute('''SELECT math_tags.feature, govern_models.model
                            FROM math_annotation
                            LEFT JOIN math_tags 
                                ON math_annotation.feature_id = math_tags.id
                            LEFT JOIN govern_models
                                ON math_annotation.govern_model_id = govern_models.id
                            LEFT JOIN tokens
                                ON tokens.token = math_annotation.annot_text
                            LEFT JOIN grammar_annotation
                                ON grammar_annotation.token_id = tokens.id
                            LEFT JOIN lemmas
                                ON grammar_annotation.lemma_id = lemmas.id
                            WHERE lemmas.name = ?
                            LIMIT 1''', (lemma,))
        return self.cur.fetchone()

    def get_math_pics(self):
        self.cur.execute('''SELECT math_tagname, filename
                            FROM math_imgs''')
        return self.cur.fetchall()

    # def find_math_markup_for_lemma(self, lemma):
    #     lemma = lemma.lower()
    #     self.cur.execute('''SELECT math_imgs.filename
    #                         FROM math_imgs
    #                         JOIN math_tags2
    #                         ON math_tags2.tag = math_imgs.math_tagname
    #                         LEFT JOIN math_entities_annot
    #                         ON math_tags2.id = math_entities_annot.id
    #                         LEFT JOIN math_entity_tokens
    #                         ON math_entity_tokens.math_entity_id = math_entities_annot.id
    #                         LEFT JOIN grammar_annotation
    #                         ON grammar_annotation.token_id = math_entity_tokens.token_id
    #                         LEFT JOIN lemmas
    #                         ON lemmas.id = grammar_annotation.lemma_id
    #                         WHERE lemmas.name = ?
    #                         LIMIT 1''', (lemma,))
    #     return self.cur.fetchone()

    def get_grammar_annotation(self, sent_id):
        self.cur.execute('''SELECT tokens.token, pos.name, lemmas.name
                            FROM tokens
                            LEFT JOIN grammar_annotation
                                ON grammar_annotation.token_id = tokens.id
                            LEFT JOIN pos
                                ON pos.id = grammar_annotation.pos_id
                            LEFT JOIN lemmas
                                ON lemmas.id = grammar_annotation.lemma_id
                            WHERE tokens.sent_id = (?)
                            ORDER BY tokens.word_in_sent''', (sent_id, ))
        return self.cur.fetchall()

    def get_user_by_uname(self, username):
        self.cur.execute('''SELECT *
                            FROM users 
                            WHERE username = (?)''', (username, ))
        return self.cur.fetchone()

    def get_user_password(self, username):
        self.cur.execute('''SELECT id, password, salt
                            FROM users
                            WHERE users.username == (?)''', (username,))
        self.cur.fetchone()

    def add_user(self, username, password, salt, email):
        self.cur.execute('''INSERT INTO users (username, password, salt, email)
                              VALUES (?, ?, ?, ?)''', (username, password, salt, email))
        self.conn.commit()

    def get_pos_tags(self):
        self.cur.execute('''SELECT name, description_rus, description_eng, examples, UD_link
                            FROM pos
                            ORDER BY name''')
        return self.cur.fetchall()
