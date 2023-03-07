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
        lemma = lemma.lower()
        self.cur.execute('''WITH tokenid AS (
                                SELECT grammar_annotation.token_id 
                                FROM grammar_annotation
                                LEFT JOIN lemmas
                                    ON lemmas.id = grammar_annotation.lemma_id
                                WHERE lemmas.name = (?)
                                LIMIT 1) 
                            SELECT math_tags.feature, govern_models.model
                            FROM math_annotation
                            LEFT JOIN math_tags 
                                ON math_annotation.feature_id = math_tags.id
                            LEFT JOIN govern_models
                                ON math_annotation.govern_model_id = govern_models.id
                            WHERE math_annotation.id_token_start <= (SELECT * FROM tokenid)
                            AND math_annotation.id_token_end >= (SELECT * FROM tokenid)
                            LIMIT 1''', (lemma,))
        return self.cur.fetchone()

    def get_math_pics(self):
        self.cur.execute('''SELECT math_tagname, filename
                            FROM math_imgs''')
        return self.cur.fetchall()

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

    def get_user_info(self, username):
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
        self.cur.execute('''SELECT name, description, examples
                            FROM pos''')
        return self.cur.fetchall()
