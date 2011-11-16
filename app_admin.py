# -*- coding: utf-8 -*-
"""
Control panel of the app, containing constants
and admin stuff.
"""

import sys
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
   term = db.StringProperty()
   term_valid = db.BooleanProperty()
   last_run = db.DateTimeProperty()
   relevant_ids = db.TextProperty()
   irrelevant_ids = db.TextProperty()


def term_key():
    """Construct a datastore key for a Term entity."""
    return db.Key.from_path('Term', '1')


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
