from dataclasses import dataclass
from typing import Iterable


@dataclass
class TokenInfo:
    token: str
    color: str


@dataclass
class ResultTokenInfo(TokenInfo):
    "Датакласс для токенов в выдаче корпуса"

    color: str = 'black'
    pos: str = None
    lemma: str = None


@dataclass
class QueryTokenInfo(TokenInfo):
    "Датакласс для токенов из запроса"

    color: str = 'green'
    model: str = None
    pos: str = None
    lemma: str = None


@dataclass
class ResultInfo:
    "Датакласс для предложения из выдачи"

    tokens: Iterable[ResultTokenInfo] = None
    youtube_link: str = None


@dataclass
class QueryInfo:
    "Датакласс со всей информацией о запросе"

    text: str
    tokens: Iterable[QueryTokenInfo] = None
    translation: str = None
    pos_string: str = None
    lemmatized: str = None
    pictures: list = None