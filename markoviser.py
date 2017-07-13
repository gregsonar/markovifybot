from bs4 import BeautifulSoup
import markovify
import random
import re
import requests
import socket

from config import config


RUBBISH_HTML = {'style', 'script', '[document]', 'head', 'title'}
USEFUL_HTML = {'p'}
MIN_PARAGRAPHS = 4
MAX_PARAGRAPHS = 8
MIN_SENTENCES = 2
MAX_SENTENCES = 6


class HTTPRequestErrorException(Exception):
    pass


class MarkovGeneratorErrorException(Exception):
    pass


rx_multiline = re.compile('\n+')
rx_multispace = re.compile(' +')
class Markoviser(object):
    @classmethod
    def from_url(cls, url):
        m = cls()
        m.process(m.fetch(url))
        return m

    @classmethod
    def from_text(cls, text):
        m = cls()
        m.process(text)
        return m

    def process(self, corpus):
        corpus = self.clean_corpus(corpus)
        self.text_model = markovify.Text(corpus, state_size=1)
        self.spam = self.generate_spam()

    def fetch(self, url):
        try:
            s = requests.session()
            s.mount('http://', requests.adapters.HTTPAdapter(max_retries=3))
            s.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))
            headers = {'User-Agent': config['misc']['user_agent']}
            response = s.get(url, headers=headers, timeout=3)
        except (requests.exceptions.RequestException, socket.timeout) as e:
            raise HTTPRequestErrorException

        # I don't think this can error out...
        soup = BeautifulSoup(response.text, 'html.parser')
        # remove all rubbish
        [s.extract() for s in soup(RUBBISH_HTML)]
        # take everything that's gud
        return [s.text for s in soup(USEFUL_HTML)]

    @staticmethod
    def clean_corpus(self, corpus):
        corpus = corpus.replace('\r', '\n')
        corpus = rx_multiline.sub('\n', corpus)
        tmp = []
        for line in corpus.split('\n'):
            line = line.strip()
            if line.endswith('.'):
                tmp.append(line)
            else:
                tmp.append(line + '.')
        corpus = ' '.join(tmp)
        corpus = corpus.replace('\n', ' ')
        corpus = rx_multispace.sub(' ', corpus)
        return corpus

    def generate_spam(self):
        paragraphs = []
        for i in range(random.randint(MIN_PARAGRAPHS, MAX_PARAGRAPHS)):
            sentences = []
            for j in range(random.randint(MIN_SENTENCES, MAX_SENTENCES)):
                sentence = self.text_model.make_sentence(tries=10000)
                if sentence:
                    sentences.append(sentence)
                else:
                    raise MarkovGeneratorErrorException
            paragraphs.append(' '.join(sentences))
        result = '\n\n'.join(paragraphs)
        return result
