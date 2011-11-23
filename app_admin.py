# -*- coding: utf-8 -*-
"""
Control panel of the app, containing constants and admin stuff.

To edit the datastore with the remote API shell run from the
Linux command line:

path/to/google_appengine/remote_api_shell.py pubcron

This starts a Python-like shell where you need to import the
Google db module and this module because it constains the model
for the datastore.

from google.appengine.ext import db
import app_admin

Get the data as follows:
entries = app_admin.UserData.all().fetch(10) # Or more.

Get the field value as follows:
entries[0].irrelevant_ids

And save them like that:
entries[0].put()
"""

import sys
import random
import traceback

from google.appengine.api import mail
from google.appengine.ext import db

# -------------------------------------------------------------------
admail = 'pubcron.mailer@gmail.com'
RETMAX = 200 
MAXHITS = 40
# -------------------------------------------------------------------

class UserData(db.Model):
   """Store user term query and date lat run."""
   user = db.UserProperty()
   uid = db.StringProperty()
   salt = db.StringProperty()
   term = db.StringProperty()
   term_valid = db.BooleanProperty()
   last_run = db.DateTimeProperty()
   relevant_ids = db.TextProperty()
   irrelevant_ids = db.TextProperty()


def term_key():
   """Construct a datastore key for a Term entity."""
   return db.Key.from_path('Term', '1')

def init_data(user):
   """Initialize UserData for a new user."""
   # Instantiate.
   user_data = UserData(term_key())

   # Initialize values.
   user_data.user = user
   user_data.uid = user.user_id()
   # We need some randomness for the salt.
   user_data.salt = unicode(random.random())
   user_data.relevant_ids = db.Text(u'')
   user_data.irrelevant_ids = db.Text(u'')

   # Put and return.
   user_data.put()
   return user_data



def mail_admin(useremail, msg=None):
   """Send a mail to admin. If no message is specified,
   send an error traceback."""

   if msg is None:
      msg = ''.join(traceback.format_exception(
         sys.exc_type,
         sys.exc_value,
         sys.exc_traceback
      ))

   mail.send_mail(
       admail,
       admail,
       "Pubcron mail report",
       "Error report for user %s:\n%s" % (useremail, msg)
   )
