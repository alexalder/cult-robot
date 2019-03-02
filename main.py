# -*- coding: utf-8 -*-

# Base imports
import json
import logging
import random
import urllib.request, urllib.parse, urllib.error
import re as regex
import datetime
import time
import sys
import requests

# Standard app engine imports
from flask import Flask, render_template, request

# Locals
import passwords
import changelog
from cultassistant import CultTextAssistant

# Configuration
app = Flask(__name__)

BASE_URL = 'https://api.telegram.org/bot' + passwords.telegram_token + '/'

assistant = CultTextAssistant()

# Logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


def log(e):
    logging.error(e)
    send("ERROR!:" + e, -1001229811735)


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
    except Exception as e:
        resp = "Error"
        log(e)
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
    is_forward = message.get('forward_from')
    
    if (not text) or is_forward:
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

    # Check if the message only contains the s/pattern/repl/ syntax, plus match flags at the end.
    # Since only the "i" flag is available for now, we'll match zero or one characters.
    def filtersed():
        try:
            pattern = regex.compile("^s([^a-zÀ-ÿ\s]).*\\1.*\\1.?$", regex.IGNORECASE)
            if pattern.match(text) and sed() is not None:
                return True
            return False
        except:
            return False

    def filteryn():
        pattern = regex.compile("(^|.*\s+)y\/n\s*$", regex.IGNORECASE)  # y/n can be the only or last pattern in a message
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
        
            return out

    def sed():
        m = regex.match(r"^s(?P<delimiter>.)", text)
        sub = regex.split(r"(?<!\\)" + regex.escape(m.group("delimiter")), text)
        if "i" in sub[3]:
            result = regex.sub(sub[1], sub[2], reply_text, flags=regex.IGNORECASE)    # if "i" is after the last delimiter, sub by ignoring case
        else:
            result = regex.sub(sub[1], sub[2], reply_text)                            # else just sub normally
        return result

    def askgoogle(query):
        display_text = assistant.assist(text_query=query)
        if display_text is None:
            return reply("Non so rispondere, bopo")
        else:
            return reply(display_text)

    def tapmusic(tapusername):
        try:
            img_data = requests.get("http://tapmusic.net/collage.php?user=" + tapusername + "&type=7day&size=5x5&caption=true&playcount=true").content
            with open('/tmp/image_name.jpg', 'wb+') as handler:
                handler.write(img_data)
            url = BASE_URL + "sendPhoto"
            files = {'photo': open('/tmp/image_name.jpg', 'rb')}
            data = {'chat_id': chat_id, 'reply_to_message_id': str(message_id)}
            return requests.post(url, files=files, data=data)
        except Exception:
            reply("Errore nella gestione del comando")
            return render_template('Error getting tapmusic'), 400

    def pinreply():
        try:
            pin = message.get('reply_to_message').get('message_id')
            res = urllib.request.urlopen(BASE_URL + 'pinChatMessage', urllib.parse.urlencode({
                'chat_id': str(chat_id),
                'message_id': str(pin),
                'disable_notification': 'true', }).encode("utf-8")).read()
            return res
        except Exception:
            reply("Rispondi a un messaggio, silly petta!")

    def getavatar(user_id):
        query = urllib.request.urlopen(BASE_URL + 'getUserProfilePhotos', urllib.parse.urlencode({
            'user_id': str(user_id),
        }).encode("utf-8")).read()
        answer = json.loads(query).get("result")
        #photo_number = answer.get('total_count')
        last_photo = answer.get('photos')[0][0].get('file_id')
        return last_photo

    def sendphoto(file_id, reply_to=None):
        try:
            resp = urllib.request.urlopen(BASE_URL + 'sendPhoto', urllib.parse.urlencode({
                'chat_id': str(chat_id),
                'photo': file_id,
                'parse_mode': 'Markdown',
                'reply_to_message_id': str(reply_to),
            }).encode("utf-8")).read()
            logging.info('send photo:')
            logging.info(resp)
        except Exception as e:
            resp = render_template('Error sending photo'), 400
            log(e)
        finally:
            return resp
    
    
    def roll(rolls):
        output = ""

        try:
            i = 0
            while i < len(rolls):
                if rolls[i] == '+':
                    rolls[i - 1:i + 2] = [''.join(rolls[i - 1:i + 2])]
                else:
                    i += 1

            for element in rolls:
                results = []
                dices = element.split('+')
                for dice in dices:

                    values = dice.split("d")

                    if values[0] == '':
                        times = 1
                    else:
                        times = int(values[0])
                    faces = int(values[1])

                    if times < 0:
                        raise Exception
                    elif times > 50 or faces <= 1:
                        return "Bel meme"

                    while times != 0:
                        roll = random.randint(1, int(values[1]))
                        results += [roll]
                        times -= 1

                sumout = str(sum(results))

                resultsout = str(results[0])

                if len(results) > 1:
                    resultsout = str(results[0])
                    for result in results[1:]:
                        resultsout += " + " + str(result)
                    output += "Hai rollato " + resultsout + " = " + sumout + ".\n"
                else:
                    output += "Hai rollato " + resultsout + ".\n"

            return(output)
        except Exception:
            return("sintassi errata!")
    

    # Quick message reply function.
    def reply(msg, replying=str(message_id)):
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
        finally:
            return resp

    if text.startswith('/'):

        # OFFICIAL COMMANDS
        # Check if bot is alive.
        if text.startswith('/ping'):
            answers = ['Welo', 'Bopo']
            return reply(random.choice(answers))
    
        # Baraldigen. Generates Baraldi-like sentences about Donne.
        elif text.startswith('/baraldi'):
            bar = json.load(open("textdatabase.json"), encoding='utf-8')
            return reply("Le donne sono come " + random.choice(bar["metaphor1"]) + ": " + random.choice(bar["metaphor2"]) +
                  " " + random.choice(bar["conjunction"]) + " " + random.choice(bar["metaphor3"]))
        
        # Eightball. Picks a random answer from the possible 20.
        elif text.startswith('/8ball'):
            database = json.load(open("textdatabase.json"), encoding='utf-8')
            return reply(random.choice(database["8ball"]))
    
        # TapMusic. Sends a collage based on the user's weekly Last.fm charts.
        elif text.startswith('/tapmusic'):
                if len(text.split()) >= 2:
                    tapusername = text.split()[1]
                    return tapmusic(tapusername)

        # Roll. Throws a dice, or more.
        elif text.startswith('/roll'):
                if len(text.split()) >= 2:
                    return reply(roll(text.split()[1:]))
                else:
                    return reply("Utilizzo: /roll 4d3, /roll 3d5 + 2d3")

        # Changelog.
        elif text.startswith('/changelog'):
            return reply(changelog.logString)

        # REPLY COMMANDS
        # Pin the message Petta replied to.
        elif text == '/pin' and int(fr_id) == 178593329:
            return pinreply()

        # Spongebob mocks the message the user replied to.
        elif text in ['/mock', '/spongemock', '/mockingbob']:
            return reply(mock())

    # OTHER COMMANDS
    # Classic stream editor.
    elif filtersed():
        return reply(sed(), reply_message.get('message_id'))

    # Random answer between yes or no.
    elif filteryn():
        answers = ['y', 'n']
        return reply(random.choice(answers))

    elif uniformed_text.startswith(("cultbot", "cultrobot", "cult bot", "cult robot")):
        if len(text.split('ot', 1)) == 2:
            if text.split('ot', 1)[1]:
                return askgoogle(text.split('ot', 1)[1])

    elif text == '!avi':
        return sendphoto(getavatar(reply_message.get('from').get('id')), reply_message.get('message_id'))

    # Private chat answers.
    else:
        if chat_id == fr_id:
            return reply('Ho ricevuto il messaggio ma non so come rispondere')

    return json.dumps(body)


# Called at 5:00 every day.
@app.route('/bopo')
def bopo_handler():
    try:
        # TO DO delay = random.randint(10, 7200)
        # deferred.defer(send, "Bopo", -1001073393308, _countdown=delay)
        return send("BOPO", -1001073393308)
    except Exception as e:
        log(e)


# Called at 18:00 every day.
@app.route('/peak')
def peak_handler():
    try:
        # Music Monday.
        if datetime.datetime.today().weekday() == 0:
            query = urllib.request.urlopen(BASE_URL + 'getChat', urllib.parse.urlencode({
                                                                              'chat_id': str(-1001073393308),
                                                                              }).encode("utf-8")).read()
            thischat = json.loads(query)
            alert = send('MUSIC MONDAY', -1001073393308)
            # Pins the alert only if there's no current pinned message or it is older than a working day.
            if thischat.get('result').get('pinned_message') is None or (time.mktime(datetime.datetime.now().timetuple()) - thischat.get('result').get('pinned_message').get('date')) > 54000:
                return urllib.request.urlopen(BASE_URL + 'pinChatMessage', urllib.parse.urlencode({
                                                                              'chat_id': str(-1001073393308),
                                                                              'message_id': str(json.loads(alert).get('result').get('message_id')),
                                                                              'disable_notification': 'true', }).encode("utf-8")).read()
    except Exception as e:
        log(e)
