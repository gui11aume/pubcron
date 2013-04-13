# -*- coding:utf-8 -*-

from google.appengine.ext import db
from random import random

# Globals.
EMPTY_LIST = 'x\x9c\x8b\x8e\x05\x00\x01\x15\x00\xb9' # compression of '[]'
EMPTY_DICT = 'x\x9c\xab\xae\x05\x00\x01u\x00\xf9'    # compression of '{}'

class UserData(db.Model):
   """Store user term query and date lat run."""
   user = db.UserProperty()
   salt = db.StringProperty()
   term = db.StringProperty()
   term_valid = db.BooleanProperty()
   mu_corpus = db.BlobProperty()
   relevant_docs = db.BlobProperty()
   irrelevant_docs = db.BlobProperty()
   last_run = db.DateTimeProperty()

def init_data(user):
   """Initialize UserData for a new user."""
   # Instantiate.
   data = UserData(
      key_name = user.user_id(),
      user = user,
      salt = unicode(random()),
      mu_corpus = EMPTY_DICT,
      relevant_docs = EMPTY_LIST,
      irrelevant_docs = EMPTY_LIST,
   )
   # Save to the datastore and return.
   data.put()
   return data
