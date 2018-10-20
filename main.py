# -*- coding: utf-8 -*-

# Base imports
import io
import json
import logging
import random
import urllib.request, urllib.parse, urllib.error
import re as regex
import datetime
import time
import sys

# Standard app engine imports
from flask import Flask, render_template, request

# Locals
import passwords

# Configuration
app = Flask(__name__)

BASE_URL = 'https://api.telegram.org/bot' + passwords.telegram_token + '/'

# Logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

def log(e):
    logging.error(e)
    send("ERROR!:" + e,-1001229811735)

# Telegram webhook handling
@app.route('/me')
def me_handler():
    return json.dumps(json.load(urllib.request.urlopen(BASE_URL + 'getMe')))

@app.route('/updates')
def updates_handler():
    return json.dumps(json.load(urllib.request.urlopen(BASE_URL + 'getUpdates')))

@app.route('/set_webhook')
def set_webhook():
    url = request.values.get('url')
    if url:
        return json.dumps(json.load(urllib.request.urlopen(BASE_URL + 'setWebhook', urllib.parse.urlencode({'url': url}).encode("utf-8"))))

# Returns the sent message as JSON
def send(msg, chat_id):
    try:
        resp = urllib.request.urlopen(BASE_URL + 'sendMessage', urllib.parse.urlencode({
                                                                          'chat_id': str(chat_id),
                                                                          'text': msg.encode('utf-8'),
                                                                          'parse_mode': 'Markdown',
                                                                          'disable_web_page_preview': 'true',
                                                                          }).encode("utf-8")).read()
        logging.info('send message:')
        logging.info(resp)
    except Exception as e: log(e)
    return resp


# Messages handling
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    body = request.get_json()
    logging.info('Request body:')
    logging.info(body)

    update_id = body['update_id']
    try:
        message = body['message']
    except:
        message = body['edited_message']
    message_id = message.get('message_id')
    date = message.get('date')
    text = message.get('text')
    
    if not text:
        logging.info('no text')
        return json.dumps(body)
    
    # Useful variables
    uniformed_text = text.lower()
    fr = message.get('from')
    fr_id = fr.get('id')
    chat = message['chat']
    chat_id = chat['id']
    reply_message = None
    reply_text = None
    if message.get('reply_to_message') is not None:
        reply_message = message.get('reply_to_message')
        if message.get('reply_to_message').get('text') is not None:
            reply_text = message.get('reply_to_message').get('text')
    
    # Command handlers
    def filtersed():
        try:
            pattern = regex.compile("^s([^a-zÀ-ÿ\s]).*\\1.*\\1.?$", regex.IGNORECASE)   # Check if the message only contains the s/pattern/repl/ syntax, plus match flags at the end. Since only the "i" flag is available for now, we'll match zero or one characters
            if pattern.match(text) and sed() is not None:
                return True
            return False
        except:
            return False

    def filteryn():
        pattern = regex.compile("(^|.*\s+)y\/n\s*$", regex.IGNORECASE)    # y/n can be the only or last pattern in a message
        return pattern.match(text)

    def mock(diversity_bias=0.5, random_seed=None):
        if reply_text:
            random.seed(random_seed)
            out = ''
            last_was_upper = True
            swap_chance = 0.5
            for c in reply_text:
                if c.isalpha():
                    if random.random() < swap_chance:
                        last_was_upper = not last_was_upper
                        swap_chance = 0.5
                    c = c.upper() if last_was_upper else c.lower()
                    swap_chance += (1-swap_chance)*diversity_bias
                out += c
        
            return(out)

    def sed():
        m = regex.match(r"^s(?P<delimiter>.)", text)
        sub = regex.split(r"(?<!\\)" + regex.escape(m.group("delimiter")), text)
        if "i" in sub[3]:
            result = regex.sub(sub[1], sub[2], reply_text, flags=regex.IGNORECASE)    # if "i" is after the last delimiter, sub by ignoring case
        else:
            result = regex.sub(sub[1], sub[2], reply_text)                            # else just sub normally
        return(result)

    # Quick message reply function.
    def reply(msg, replying = str(message_id)):
        try:
            resp = urllib.request.urlopen(BASE_URL + 'sendMessage', urllib.parse.urlencode({
                'chat_id': str(chat_id),
                'text': msg.encode('utf-8'),
                'disable_web_page_preview': 'true',
                'reply_to_message_id': replying,
            }).encode("utf-8")).read()

            logging.info('Send response:')
            logging.info(resp)
        except Exception:
            logging.exception("Exception in reply:")

    if text.startswith('/'):
        
        
        # OFFICIAL COMMANDS
        # Check if bot is alive.
        if text.startswith('/ping'):
            answers = ['Welo', 'Bopo']
            reply(random.choice(answers))
    
        # Baraldigen. Generates Baraldi-like sentences about Donne.
        if text.startswith('/baraldi'):
            bar = json.load(open("baraldi.json"), encoding='utf-8')
            reply("Le donne sono come " + random.choice(bar["metaphor1"]) + ": " + random.choice(bar["metaphor2"]) +
                  " " + random.choice(bar["conjunction"]) + " " +random.choice(bar["metaphor3"]))
        
        # Eightball. Picks a random answer from the possible 20.
        if text.startswith('/8ball'):
            answers = ["It is certain", "It is decidedly so", "Without a doubt", "Yes definitely", "You may rely on it", "As I see it, yes", "Most likely", "Outlook good", "Yes", "Signs point to yes", "Reply hazy try again", "Ask again later", "Better not tell you now", "Cannot predict now", "Concentrate and ask again", "Don't count on it", "My reply is no", "My sources say no", "Outlook not so good", "Very doubtful"]
            reply(answers[random.randint(1,8)])
        
        # Changelog.
        if text.startswith('/changelog'):
            reply("1.0: Trasposto nonmaterialbot su piattaforma GCloud, codice disponibile via https://github.com/alexalder/cult-robot")

        
        # REPLY COMMANDS
        # Pin the message Petta replied to.
        if text == '/pin' and int(fr_id) == 178593329:
            try:
                pin = message.get('reply_to_message').get('message_id')
                urllib.request.urlopen(BASE_URL + 'pinChatMessage', urllib.parse.urlencode({
                                                                      'chat_id': str(chat_id),
                                                                      'message_id': str(pin),
                                                                      'disable_notification': 'true',}).encode("utf-8")).read()
            except Exception:
                reply("Rispondi a un messaggio, silly petta!")

            
        # Spongebob mock the message the user replied to.
        if text in ['/mock', '/spongemock', '/mockingbob']:
            reply(mock())


    # OTHER COMMANDS
    # Classic stream editor.
    elif filtersed():
        reply(sed(), reply_message.get('message_id'))

    # Random answer between yes or no.
    elif filteryn():
        answers = ['y', 'n']
        reply(random.choice(answers))

    # Private chat answers.
    else:
        if (chat_id == fr_id):
            reply('Ho ricevuto il messaggio ma non so come rispondere')

    return json.dumps(body)


# Called at 5:00 every day.
@app.route('/bopo')
def bopo_handler():
    try:
        #TO DO delay = random.randint(10, 7200)
        #deferred.defer(send, "Bopo", -1001073393308, _countdown=delay)
        send("BOPO", -1001073393308)
    except Exception as e:
        log(e)

# Called at 18:00 every day.
@app.route('/peak')
def peak_handler():
    try:
        # Music Monday.
        if (datetime.datetime.today().weekday() == 0):
            query = urllib.request.urlopen(BASE_URL + 'getChat', urllib.parse.urlencode({
                                                                              'chat_id': str(chat_id),
                                                                              }).encode("utf-8")).read()
            thischat = json.loads(query)
            alert = send('MUSIC MONDAY', -1001073393308)
            # Pins the alert only if there's no current pinned message or it is older than a working day.
            if (thischat.get('result').get('pinned_message') is None or (time.mktime(datetime.datetime.now().timetuple()) - thischat.get('result').get('pinned_message').get('date')) > 54000):
                urllib.request.urlopen(BASE_URL + 'pinChatMessage', urllib.parse.urlencode({
                                                                              'chat_id': str(chat_id),
                                                                              'message_id': str(json.loads(alert).get('result').get('message_id')),
                                                                              'disable_notification': 'true',}).encode("utf-8")).read()
    except Exception as e:
        log(e)
