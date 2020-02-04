
# -*- coding: utf-8 -*-

# Base imports
import json
import logging
import random
import urllib.request, urllib.parse, urllib.error
import re
import datetime
import time
import sys
import requests
import traceback

# Standard app engine imports
from flask import Flask, request, make_response
from google.cloud import firestore

# Locals

from pettagram.pettagram import Bot
import changelog
from cultassistant import CultTextAssistant

# Configuration
app = Flask(__name__)

#Datastore
db = firestore.Client()

secrets = db.collection('data').document('secrets').get().to_dict()

bot = Bot('https://api.telegram.org/bot' + secrets['telegram_token'] + '/')

# Logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


def log(e):
    logging.error(e)
    bot.send(secrets['report_id'], msg="ERROR!:" + e)


# Initializing cult assistant

assistant = CultTextAssistant(secrets['assistant_secret']['installed'])


# Telegram webhook handling
@app.route('/me')
def me_handler():
    return json.dumps(json.load(urllib.request.urlopen(bot.base_url + 'getMe')))


@app.route('/updates')
def updates_handler():
    return json.dumps(json.load(urllib.request.urlopen(bot.base_url + 'getUpdates')))


@app.route('/set_webhook')
def set_webhook():
    url = request.values.get('url')
    if url:
        return json.dumps(json.load(urllib.request.urlopen(
            bot.base_url + 'setWebhook', urllib.parse.urlencode({'url': url}).encode('utf-8'))))


# Messages handling
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    body = request.get_json()
    logging.info('Request body:')
    logging.info(body)

    update_id = body['update_id']
    try:
        message = body['message']
        if not message:
            message = body['edited_message']
        text = message.get('text')
        is_forward = 'forward_date' in message
    except:
        logging.info('unhandled message')
        return json.dumps(body)

    if not text or is_forward:
        logging.info('no text')
        return json.dumps(body)
    
    # Useful variables
    message_id = message.get('message_id')
    date = message.get('date')
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
            pattern = re.compile("^s([^a-zÀ-ÿ\s]).*\\1.*\\1.?$", re.IGNORECASE)
            if pattern.match(text) and sed() is not None:
                return True
            return False
        except:
            return False

    def filteryn():
        # y/n can be the only or last pattern in a message
        pattern = re.compile("(^|.*\s+)y\/n\s*$", re.IGNORECASE)
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
        else:
            return "No, tu"

    def sed():
        m = re.match(r"^s(?P<delimiter>.)", text)
        sub = re.split(r"(?<!\\)" + re.escape(m.group("delimiter")), text)
        if "i" in sub[3]:
            result = re.sub(sub[1], sub[2], reply_text, flags=re.IGNORECASE)    # if "i" is after the last delimiter, sub by ignoring case
        else:
            result = re.sub(sub[1], sub[2], reply_text)                            # else just sub normally
        return result

    def eight_ball():
        database = json.load(open("textdatabase.json"), encoding='utf-8')
        return random.choice(database["8ball"])

    def askgoogle(query):
        if not assistant.ready:
            return bot.send(chat_id, msg=eight_ball(), reply=message_id)
        display_text = assistant.assist(text_query=query)
        if display_text is None:
            if query[-1] == "?":
                return bot.send(chat_id, msg=eight_ball(), reply=message_id)
            return make_response('Empty string')
        else:
            display_text = re.sub("google", "CULT", display_text, flags=re.IGNORECASE)
            return bot.send(chat_id, msg=display_text, reply=message_id)

    def minecraftcheck():
        r = requests.get("https://api.mcsrvstat.us/2/93.42.109.78")
        formatted = json.loads(r.text)
        server_status = "Online" if "players" in formatted else "Offline"
        version = "N/A"
        onlineppl = ""
        if "players" in formatted:
            version = formatted["version"]
            onlineppl = formatted["players"]["online"]
        text = "cult.duckdns.org:25565\nServer: " + server_status + "\nGiocatori: " + str(onlineppl) + "\nVersione: " + version
        return text

    def tapmusic(tapusername):
        try:
            img_data = requests.get("http://tapmusic.net/collage.php?user=" + tapusername + "&type=7day&size=4x4&caption=true&playcount=true").content
            with open('/tmp/image_name.jpg', 'wb+') as handler:
                handler.write(img_data)

            bot.send_file(chat_id, photo='/tmp/image_name.jpg', reply=str(message_id))

            return make_response('Successfully got Tapmusic')
        except urllib.error.HTTPError as e:
            return bot.send(chat_id, msg="Errore nella gestione del comando: " + e.read().decode(), reply=message_id)
        except Exception as e:
            return bot.send(chat_id, msg="Errore nella gestione del comando: " + e, reply=message_id)

    def cultphoto(file_id):
        try:
            file_path = bot.get_file(file_id)
            full_path = 'https://api.telegram.org/file/bot' + secrets['telegram_token'] + '/' + file_path
            img_data = requests.get(full_path).content
            with open('/tmp/image_name.jpg', 'wb+') as handler:
                handler.write(img_data)

            url = bot.base_url + "setChatPhoto"
            files = {'photo': open('/tmp/image_name.jpg', 'rb')}
            data = {'chat_id': chat_id}
            requests.post(url, files=files, data=data)

            return make_response('Successfully updated cult photo')
        except urllib.error.HTTPError as e:
            return bot.send(chat_id, msg="Errore nella gestione del comando: " + e.read().decode(), reply=message_id)
        except Exception as e:
            return bot.send(chat_id, msg="Errore nella gestione del comando: " + e, reply=message_id)

    def cultname(newname):
        try:
            fullname = 'CULT - ' + str(newname)
            res = urllib.request.urlopen(bot.base_url + 'setChatTitle', urllib.parse.urlencode({
                'chat_id': str(chat_id),
                'title': fullname, }).encode("utf-8")).read()
            return res
        except Exception as e:
            logging.info(e)
            return bot.send(chat_id, msg="Errore nel cambio del nome", reply=message_id)

    def getavatar(user_id):
        query = urllib.request.urlopen(bot.base_url + 'getUserProfilePhotos', urllib.parse.urlencode({
            'user_id': str(user_id),
        }).encode("utf-8")).read()
        answer = json.loads(query).get("result")
        photo_array = answer.get('photos')
        last_photo = None
        if photo_array:
            last_photo = photo_array[0][0].get('file_id')
        return last_photo
    
    def filterref():
        patterns = '/dp|/gp/product|amzn'
        return re.search(patterns, text)
    
    def reflink(link):
        product_code = ""
        if "/dp" in link:
            product_code = re.split('[^0-9a-zA-Z]', link.split("/dp/")[1])[0]
        elif "/gp/product" in link:
            product_code = re.split('[^0-9a-zA-Z]', link.split("/gp/product/")[1])[0]
        elif "amzn" in link:
            r = requests.head(link, allow_redirects=True)
            return reflink(r.url)
        if product_code:
            return bot.send(chat_id, msg="http://www.amazon.it/dp/" + product_code + "/?tag=" + secrets['amazon_tag'], reply=message_id)

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

            return output
        except Exception:
            return "sintassi errata!"

    if text.startswith('/'):

        # OFFICIAL COMMANDS
        # Check if bot is alive.
        if text.startswith('/ping'):
            answers = ['Welo', 'Bopo']
            return bot.send(chat_id, msg=random.choice(answers), reply=message_id)

        elif text.startswith('/minecraft'):
            return bot.send(chat_id, msg=minecraftcheck(), reply=message_id)
    
        # Baraldigen. Generates Baraldi-like sentences about Donne.
        elif text.startswith('/baraldi'):
            bar = json.load(open("textdatabase.json"), encoding='utf-8')
            res = "Le donne sono come " + random.choice(bar["metaphor1"]) + ": " + random.choice(bar["metaphor2"]) + \
                  " " + random.choice(bar["conjunction"]) + " " + random.choice(bar["metaphor3"])
            return bot.send(chat_id, msg=res, reply=message_id)
        
        # Eightball. Picks a random answer from the possible 20.
        elif text.startswith('/8ball'):
            return bot.send(chat_id, msg=eight_ball(), reply=message_id)
    
        # TapMusic. Sends a collage based on the user's weekly Last.fm charts.
        elif text.startswith('/tapmusic'):
                if len(text.split()) >= 2:
                    tapusername = text.split()[1]
                    return tapmusic(tapusername)

        # Roll. Throws a dice, or more.
        elif text.startswith('/roll'):
                if len(text.split()) >= 2:
                    return bot.send(chat_id, msg=roll(text.split()[1:]), reply=message_id)
                else:
                    return bot.send(chat_id, msg="Utilizzo: /roll 4d3, /roll 3d5 + 2d3", reply=message_id)

        # Changelog.
        elif text.startswith('/changelog'):
            return bot.send(chat_id, msg=changelog.logString, reply=message_id)

        # REPLY COMMANDS
        # Pin the message Petta replied to.
        elif text == '/pin' and int(fr_id) == secrets['bot_admin_id']:
            return bot.pin(reply_message.get('message_id'), chat_id, False)

        elif text == '/cultname' and int(chat_id) == secrets['group_id']:
            if reply_text and len(reply_text) <= 25:
                return cultname(reply_text)

        elif text == '/cultphoto' and int(chat_id) == secrets['group_id']:
            if reply_message is not None:
                if reply_message.get('photo') is not None:
                    photo_id = reply_message.get('photo')[-1].get('file_id')
                    return cultphoto(photo_id)

        elif text == '/kickme':
            bot.send(chat_id, sticker_id='CAACAgQAAxkBAAJbjV45Rv3jjxrSY3kjrJ1dBH6BZIBYAAILBAACdgABOVLk_1CaDVyabRgE')
            return bot.kick(chat_id, fr_id)

        # Spongebob mocks the message the user replied to.
        elif text in ['/mock', '/spongemock', '/mockingbob']:
            return bot.send(chat_id, msg=mock(), reply=message_id)

    # OTHER COMMANDS
    # Classic stream editor.
    elif filtersed():
        return bot.send(chat_id, msg=sed(), reply=message_id)

    # Random answer between yes or no.
    elif filteryn():
        answers = ['y', 'n']
        return bot.send(chat_id, msg=random.choice(answers), reply=message_id)

    elif uniformed_text.startswith(("cultbot", "cultrobot", "cult bot", "cult robot")):
        if len(text.split('ot', 1)) == 2:
            query = text.split('ot', 1)[1]
            if 0 < len(query) < 100:
                return askgoogle(text.split('ot', 1)[1])

    elif text == '!avi':
        if reply_message:
            return bot.send(chat_id, photo_id=getavatar(reply_message.get('from').get('id')), reply=reply_message.get('message_id'))

    # Fallback
    else:
        if chat_id == fr_id and filterref():
                return reflink(text)
        else:
            if reply_message is not None:
                if reply_message.get('from').get('id') == secrets['bot_id']:
                    if text.endswith('?'):
                        if 0 < len(text) < 100:
                            return askgoogle(text)

    return make_response('Nothing to handle')


# Called at 5:00 every day.
@app.route('/bopo')
def bopo_handler():
    try:
        return bot.send(secrets['group_id'], msg="BOPO")
    except Exception as e:
        log(e)


@app.route('/keepalive')
def keepalive_handler():
    return make_response('Keep alive')


# Called at 18:00 every day.
@app.route('/peak')
def peak_handler():
    try:
        # Music Monday.
        if datetime.datetime.today().weekday() == 0:
            query = urllib.request.urlopen(bot.base_url + 'getChat', urllib.parse.urlencode({
                                                                              'chat_id': str(secrets['group_id']),
                                                                              }).encode("utf-8")).read()
            thischat = json.loads(query)
            alert = bot.send(secrets['group_id'], msg="MUSIC MONDAY")
            # Pins the alert only if there's no current pinned message or it is older than a working day.
            if thischat.get('result').get('pinned_message') is None or (time.mktime(datetime.datetime.now().timetuple()) - thischat.get('result').get('pinned_message').get('date')) > 54000:
                return bot.pin(str(json.loads(alert).get('result').get('message_id')), str(secrets['group_id']), False)
        return make_response('Peak hour handled')
    except Exception as e:
        log(e)
