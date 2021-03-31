import os
import telebot
from flask import Flask, request
import requests
import pandas as pd
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer #TF-IDF
from sklearn.decomposition import TruncatedSVD
from sklearn.neighbors import BallTree
from sklearn.base import BaseEstimator
from sklearn.pipeline import make_pipeline

API_TOKEN = os.environ['TOKEN']
bot = telebot.TeleBot(API_TOKEN)

server = Flask(__name__)
TELEBOT_URL = 'class-vs-dl/'
BASE_URL = 'https://class-vs-dl.herokuapp.com/'

good = pd.read_csv("good.tsv", sep='\t')

vectorizer = TfidfVectorizer()
vectorizer.fit(good.context_0)
matrix_big = vectorizer.transform(good.context_0)

svd = TruncatedSVD(n_components=300)
svd.fit(matrix_big)
matrix_small =  svd.transform(matrix_big)

def softmax(x):
  proba = np.exp(-x)
  return proba/sum(proba)

class NeighborSampler(BaseEstimator):
    def __init__(self, k=5, temperature=1.0):
        self.k = k
        self.temperature = temperature
    def fit(self, X, y):
        self.tree_ = BallTree(X)
        self.y_ = np.array(y)
    def predict(self, X, random_state=None):
        distances, indices = self.tree_.query(X, return_distance=True, k=self.k)
        result = []
        for distance, index in zip(distances, indices):
            result.append(np.random.choice(index, p=softmax(distance * self.temperature)))
            return self.y_[result]
          
ns = NeighborSampler()
ns.fit(matrix_small, good.reply)
pipe = make_pipeline(vectorizer, svd, ns)

# Handle '/start' and '/help'
@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    bot.reply_to(message, "Hi there, I am EchoBot. Just say anything nice and I'll say the exact same thing to you!")


# Handle all other messages with content_type 'text' (content_types defaults to ['text'])
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, pipe.predict([message.text.lower()])[0])

@server.route('/' + TELEBOT_URL + API_TOKEN, methods=['POST'])
def get_message():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=BASE_URL + TELEBOT_URL + API_TOKEN)
    return "!", 200

server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
webhook()
