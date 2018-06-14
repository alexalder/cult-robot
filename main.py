# -*- coding: utf-8 -*-

# Base imports
import StringIO
import json
import logging
import random
import urllib
import urllib2
import re as regex

# Standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import webapp2

# Local imports
import passwords

BASE_URL = 'https://api.telegram.org/bot' + passwords.telegram_token + '/'

class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe'))))
class GetUpdatesHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getUpdates'))))
class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        url = self.request.get('url')
        if url:
            self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': url})))))


class WebhookHandler(webapp2.RequestHandler):
    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        logging.info('Request body:')
        logging.info(body)
        self.response.write(json.dumps(body))

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
            return
        
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
            pattern = regex.compile("^s([^a-zÀ-ÿ\s]).*\\1.*\\1.?$", regex.IGNORECASE)   # Check if the message only contains the s/pattern/repl/ syntax, plus match flags at the end. Since only the "i" flag is available for now, we'll match zero or one characters
            return pattern.match(text)
        
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

        # Message send function
        def reply(msg):
            resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                'chat_id': str(chat_id),
                'text': msg.encode('utf-8'),
                'disable_web_page_preview': 'true',
                'reply_to_message_id': str(message_id),
            })).read()

            logging.info('Send response:')
            logging.info(resp)

        # COMMANDS
        if text.startswith('/'):
            
            # Check if bot is alive
            if text.startswith('/ping'):
                reply('Welo')
            
            # Eightball. Picks a random answer from the possible 20
            if text.startswith('/8ball'):
                answers = ["It is certain", "It is decidedly so", "Without a doubt", "Yes definitely", "You may rely on it", "As I see it, yes", "Most likely", "Outlook good", "Yes", "Signs point to yes", "Reply hazy try again", "Ask again later", "Better not tell you now", "Cannot predict now", "Concentrate and ask again", "Don't count on it", "My reply is no", "My sources say no", "Outlook not so good", "Very doubtful"]
                reply(answers[random.randint(1,8)])
            
            # Spongebob mock the message the user replied to
            elif text in ['/mock', '/spongemock', '/mockingbob']:
                reply(mock())

        # OTHER

        # Classic stream editor
        elif filtersed():
            reply(sed())

        # Random asnwer between yes or no
        elif filteryn():
            answers = ['y', 'n']
            reply(random.choice(answers))

        # Welo
        elif 'welo' in uniformed_text:
            reply('Welo')

        # Private chat answers
        else:
            if (chat_id == fr_id):
                reply('Ho ricevuto il messaggio ma non so come rispondere')


app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    ('/updates', GetUpdatesHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
], debug=True)
