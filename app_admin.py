# -*- coding: utf-8 -*-
"""
Control panel of the app, containing constants and admin stuff.

To edit the datastore with the remote API shell run from the
Linux command line:

path/to/google_appengine/remote_api_shell.py pubcron

This starts a Python-like shell where you need to import the
Google db module and this module because it constains the model
for the datastore.

import sys
sys.path.append('path/to/pubcron/')
import app_admin

Get the data as follows:
entries = app_admin.UserData.all().fetch(10) # Or more.

Get the field value as follows:
entries[0].irrelevant_docs

And save them like that:
entries[0].put()
"""

import sys
import zlib
try:
   import json
except ImportError:
   import simplejson as json
import random
import traceback

from google.appengine.api import mail
from google.appengine.ext import db

# -------------------------------------------------------------------
ADMAIL = 'pubcron.mailer@gmail.com'
RETMAX = 200 
MAXHITS = 40
# -------------------------------------------------------------------

# --
empty_list = 'x\x9c\x8b\x8e\x05\x00\x01\x15\x00\xb9' # compression of '[]'
empty_dict = 'x\x9c\xab\xae\x05\x00\x01u\x00\xf9'    # compression of '{}'
# --

# NB: 'db.TextProperty()' is used as JSON dump to model complex data.
# mu_corpus_json is a list of preprocessed abstract texts.
#    { pmid: [ stemmed_word1, stemmed_word2, ... ], ... }
# relevant_docs and irrelevant_docs are JSON dictionaries indexed by PMID.
# The value is an array of 2 elements: title and the tf-idf dictionary.
#    { pmid: [ title, { word1: tfidf1: word2, tfidf2, ... } ], ... }

class UserData(db.Model):
   """Store user term query and date lat run."""
   user = db.UserProperty()
   uid = db.StringProperty()
   salt = db.StringProperty()
   term = db.StringProperty()
   term_valid = db.BooleanProperty()
   last_run = db.DateTimeProperty()
   mu_corpus = db.BlobProperty()
   relevant_docs = db.BlobProperty()
   irrelevant_docs = db.BlobProperty() 


def user_key():
   """Construct a datastore key for a UserData entity."""
   return db.Key.from_path('UserData', '1')


def init_data(user):
   """Initialize UserData for a new user."""
   # Instantiate.
   user_data = UserData(user_key())

   # Initialize values.
   user_data.user = user
   user_data.uid = user.user_id()
   # We need some randomness for the salt.
   user_data.salt = unicode(random.random())
   mu_corpus = empty_dict
   user_data.relevant_docs = empty_list
   user_data.irrelevant_docs = empty_list

   # Put and return.
   user_data.put()
   return user_data


def decrypt(entity, field):
   """Convenience function to extract compressed attributes."""
   return json.loads(zlib.decompress(getattr(entity, field)))


def mail_admin(user_mail, message=None):
   """Send a mail to admin. If no message is specified,
   send an error traceback."""

   if message is None:
      message = ''.join(traceback.format_exception(
         sys.exc_type,
         sys.exc_value,
         sys.exc_traceback
      ))

   mail.send_mail(
       ADMAIL,
       ADMAIL,
       "PubCron report",
       "%s:\n%s" % (user_mail, message)
   )
