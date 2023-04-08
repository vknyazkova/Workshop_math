import flask_login
from hashlib import pbkdf2_hmac
import os

from backend.database import WebDBHandler

N_ITERS = 500


class User(flask_login.UserMixin, WebDBHandler):

    def __init__(self, db_path):
        WebDBHandler.__init__(self, db_path)
        self.email = None
        self.salt = None
        self.password = None
        self.id = None
        self.username = None

    def __repr__(self):
        return f'User {self.username}'

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.username)

    @staticmethod
    def hash_password(password, salt=None):
        if not salt:
            salt = os.urandom(12)
        password = bytes(password, encoding='utf8')
        dk = pbkdf2_hmac('sha256', password, salt, N_ITERS)
        return dk.hex(), salt

    def validate_password(self, entered):
        entered_hash, _ = User.hash_password(entered, salt=self.salt)
        if entered_hash == self.password:
            return True
        else:
            return False

    def get(self, username):
        res = self.get_user_by_uname(username)
        if res:
            self.id, self.username, self.password, self.salt, self.email = res
            return self
        else:
            return None
