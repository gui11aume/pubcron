# -*- coding: utf-8 -*-
"""
Control panel of the app, containing constants
and admin stuff.
"""

import sys
import traceback

from google.appengine.api import mail

# -------------------------------------------------------------------
admail = 'pubcron.mailer@gmail.com'
RETMAX = 200 
MAXHITS = 40
# -------------------------------------------------------------------


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
