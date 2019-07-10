from abc import ABC, abstractmethod
from base64 import b64encode, b64decode
from binascii import hexlify, unhexlify
from pickle import dump, load
from textwrap import wrap
from urllib.parse import quote_plus, unquote

class Recipe:

    def __init__(self, name, base_ingredient = None, ingredients = [], potion = None):
        self.name = name
        self.base_ingredient = base_ingredient
        self.ingredients = ingredients
        self.potion = potion

    def save(self):
        path = app.config['RECIPE_DIRECTORY'] + self.name + app.config['RECIPE_EXTENSION']
        with open(path, 'wb') as f:
            dump(self, f)

    @classmethod
    def get(cls, name):
        path = app.config['RECIPE_DIRECTORY'] + name + app.config['RECIPE_EXTENSION']
        try:
            with open(path, 'rb') as f:
                return load(f)
        except Exception:
            return cls(name)

class base64(ABC):

    @abstractmethod
    def encode(input = ''):
        return b64encode(input.encode()).decode()

    @abstractmethod
    def decode(input = ''):
        return b64decode(input).decode()

class hex(ABC):

    @abstractmethod
    def encode(input = ''):
        return '0x' + hexlify(input.encode()).decode()

    @abstractmethod
    def decode(input = ''):
        if input[:2] == '0x':
            input = input[2:]
        return unhexlify(input.encode()).decode()


class url(ABC):

    @abstractmethod
    def encode(input=''):
        return quote_plus(input)

    @abstractmethod
    def decode(input=''):
        return unquote(input)

class unicode(ABC):

    @abstractmethod
    def encode(input = ''):
        return '\\x'.join(wrap(hex.encode(input), 2))[2:]

    @abstractmethod
    def decode(input = ''):
        return hex.decode(''.join(input.split('\\x')))

