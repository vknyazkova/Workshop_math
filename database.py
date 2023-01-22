import sqlite3
from collections import namedtuple


class DBHandler:
    conn = None
    cur = None

    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cur = self.conn.cursor()

    def __del__(self):
        self.conn.close()

    def select_sentences(self, lemmatized_request):
        pattern = '%' + '%'.join(lemmatized_request) + '%'
        self.cur.execute('''SELECT id, sent, lemmatized
                            FROM sents
                            WHERE lemmatized LIKE ?''', (pattern,))
        res = self.cur.fetchall()
        SentenceInfo = namedtuple('SentenceInfo', ['id', 'sent', 'lemmatized'])
        return [SentenceInfo(*row) for row in res]