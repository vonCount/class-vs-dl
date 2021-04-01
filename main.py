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
# from elasticsearch import Elasticsearch

API_TOKEN = os.environ['TOKEN']
bot = telebot.TeleBot(API_TOKEN)

server = Flask(__name__)
TELEBOT_URL = 'class-vs-dl/'
BASE_URL = 'https://class-vs-dl.herokuapp.com/'

# bonsai = os.environ['BONSAI_URL']
# auth = re.search('https\:\/\/(.*)\@', bonsai).group(1).split(':')
# host = bonsai.replace('https://%s:%s@' % (auth[0], auth[1]), '')

# # optional port
# match = re.search('(:\d+)', host)
# if match:
#     p = match.group(0)
#     host = host.replace(p, '')
#     port = int(p.split(':')[1])
# else:
#     port=443


# # Connect to cluster over SSL using auth for best security:
# es_header = [{
#   'host': host,
#   'port': port,
#   'use_ssl': True,
#   'http_auth': (auth[0],auth[1])
# }]

# es = Elasticsearch(es_header)
# es.indices.create(index="logs")


# mapit={"log":{"properties":{"text":{"type":"text"},
#                             "response":{"type":"text"},
#                             "user_nickname":{"type":"text"},
#                             "timestamp":{"type":"date", "format":"yyyy-MM-dd'T'HH:mm:ss"}}}}

# es.indices.put_mapping(index="logs", doc_type='log', body=mapit, include_type_name=True)

# def reply_with_log(message, response):
#     e1 = {"text": message.text,
#           "response": response,
#           "user_nickname": message.from_user.username,
#           "timestamp": datetime.utcnow()}
#     es.index(index='logs',doc_type='log',body=e1)
#     bot.reply_to(message, response)

data = pd.read_csv("https://raw.githubusercontent.com/vonCount/class-vs-dl/main/good.tsv", sep='\t')

vectorizer = TfidfVectorizer()
vectorizer.fit(data.context_0)
matrix_big = vectorizer.transform(data.context_0)

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
ns.fit(matrix_small, data.reply)
pipe = make_pipeline(vectorizer, svd, ns)


@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    bot.reply_to(message, "Hi there, I am EchoBot. Just say anything nice and I'll say the exact same thing to you!")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, pipe.predict([message.text.lower()])[0])

@server.route('/' + TELEBOT_URL + API_TOKEN, methods=['POST'])
def get_message():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200

# @server.route("/show_logs")
# def show_logs():
#     messages_list = list(es.search(index = "logs", body={"query": {"match_all": {}}}))
#     result = '<div>There are {} messages total. The last 10 are: </div><table>'.format(len(messages_list))
#     row_template = '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'
#     result += row_template.format('time', 'user', 'text from user', 'response from bot')
#     for message in messages_list[-10:]:
#         result += row_template.format(
#             message['timestamp'], message['user_nickname'], message['text'], message['response']
#         )
#     result += '</table>'
#     return result, 200

@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=BASE_URL + TELEBOT_URL + API_TOKEN)
    return "!", 200

server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
webhook()
