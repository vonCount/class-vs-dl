import argparse
import os
import telebot
from datetime import datetime
from flask import Flask, request
#from pymongo import MongoClient
import os, base64, re, logging
from elasticsearch import Elasticsearch

API_TOKEN = os.environ['TOKEN']
bot = telebot.TeleBot(API_TOKEN)

# Log transport details (optional):
logging.basicConfig(level=logging.INFO)


server = Flask(__name__)
TELEBOT_URL = 'class-vs-dl/'
BASE_URL = 'https://class-vs-dl.herokuapp.com/'

#MONGODB_URI = os.environ['MONGODB_URI']
bonsai = os.environ['BONSAI_URL']
auth = re.search('https\:\/\/(.*)\@', bonsai).group(1).split(':')
host = bonsai.replace('https://%s:%s@' % (auth[0], auth[1]), '')

# optional port
match = re.search('(:\d+)', host)
if match:
    p = match.group(0)
    host = host.replace(p, '')
    port = int(p.split(':')[1])
else:
    port=443

#mongo_client = MongoClient(MONGODB_URI)

# Connect to cluster over SSL using auth for best security:
es_header = [{
  'host': host,
  'port': port,
  'use_ssl': True,
  'http_auth': (auth[0],auth[1])
}]

es = Elasticsearch(es_header)
es.indices.create(index="logs")

#mongo_db = mongo_client.get_default_database()
#mongo_logs = mongo_db.get_collection('logs')

mapit={"log":{"properties":{"author":{"type":"text"},
                                "date":{"type":"text"},
                                "time":{"type":"date", "format":"HH:mm"},
                                "difficulty":{"type":"double"},
                                "rubrics":{"type":"text","analyzer" : "russian"},
                                "text":{"type":"text","analyzer" : "russian"},
                                "title":{"type":"text","analyzer" : "russian"}}}}

mapit={"log":{"properties":{"text":{"type":"text"},
                            "response":{"type":"text"},
                            "user_nickname":{"type":"text"}
                            "timestamp":{"type":"date", "format":"yyyy-MM-dd'T'HH:mm:ss"}}}}

es.indices.put_mapping(index="logs", doc_type='log', body=mapit, include_type_name=True)

def reply_with_log(message, response):
    e1 = {"text": message.text,
          "response": response,
          "user_nickname": message.from_user.username,
          "timestamp": datetime.utcnow()}
    es.index(index='logs',doc_type='log',body=e1)
    bot.reply_to(message, response)

# Handle '/start' and '/help'
@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    reply_with_log(message, "Hi there, I am EchoBot. Just say anything nice and I'll say the exact same thing to you!")


# Handle all other messages with content_type 'text' (content_types defaults to ['text'])
@bot.message_handler(func=lambda message: True)
def echo_message(message):
    reply_with_log(message, message.text)


@server.route('/' + TELEBOT_URL + API_TOKEN, methods=['POST'])
def get_message():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=BASE_URL + TELEBOT_URL + API_TOKEN)
    return "!", 200


@server.route("/show_logs")
def show_logs():
    messages_list = list(mongo_logs.find())
    result = '<div>There are {} messages total. The last 10 are: </div><table>'.format(len(messages_list))
    row_template = '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'
    result += row_template.format('time', 'user', 'text from user', 'response from bot')
    for message in messages_list[-10:]:
        result += row_template.format(
            message['timestamp'], message['user_nickname'], message['text'], message['response']
        )
    result += '</table>'
    return result, 200


parser = argparse.ArgumentParser(description='Run the bot')
parser.add_argument('--poll', action='store_true')
args = parser.parse_args()

if args.poll:
    bot.remove_webhook()
    bot.polling()
else:
    # webhook should be set first
    webhook()
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
