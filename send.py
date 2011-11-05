# -*- coding: utf-8 -*-

import os
import sys
import datetime
import traceback

import eUtils

from pubcron import UserData, term_key
from Classify import update_score

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

############
RETMAX = 100


def mail_admin(useremail, msg):
   mail.send_mail("pubcron.mailer@gmail.com",
                  "pubcron.mailer@gmail.com",
                  "Pubcron mail report",
                  "%s:\n%s" % (useremail, msg))

class Despatcher(webapp.RequestHandler):
   """Called by the cron scheduler. Query PubMed with all the
   saved user terms and send them a mail."""

   def get(self):

      # Path to the mail html template.
      path_to_hits = os.path.join(os.path.dirname(__file__),
            'hits.html')

      # Get all users data.
      data = UserData.gql("WHERE ANCESTOR IS :1", term_key())

      for user_data in data:

         term = str(user_data.term)

         # Update last time run.
         last_run = user_data.last_run
         user_data.last_run = datetime.datetime.now()
         user_data.put()

         # Skip user if term is not valid (or empty incidentally).
         if not user_data.term_valid:
            continue

         yesterday = datetime.datetime.today() + \
               datetime.timedelta(days=-1)
         date_from = last_run or yesterday
         date_to = max(yesterday, date_from)

         term = "("+term+")" + \
               date_from.strftime("+AND+(%Y%%2F%m%%2F%d:") + \
               date_to.strftime("%Y%%2F%m%%2F%d[crdt])")

         # Fetch the abstracts.
         try:
            Abstr_list = eUtils.fetch_Abstr(
                  term = term,
                  # Limit on all queries, to keep it light.
                  retmax = RETMAX,
                  email = 'pubcron.mailer@gmail.com'
            )
            # Get the parsed abstracts with an abstract text.
            Abstr_list = [a for a in Abstr_list if hasattr(a, 'text')]

            # Write the scores in place.
            update_score(
                  Abstr_list,
                  len(user_data.relevant_ids.split(':')),
                  len(user_data.irrelevant_ids.split(':')),
                  user_data.positive_terms.split(':'),
                  user_data.negative_terms.split(':')
               )
            template_values = {
               'user': user_data.user.nickname(),
               'Abstr_list': sorted(Abstr_list, reverse=True)
            }
         except eUtils.NoHitException:
            # No hit today. Better luck tomorrow :-)
            continue
         except Exception, e:
            # For other exceptions (including PubMedExceptions), send
            # a mail to amdin.
            msg = ''.join(traceback.format_exception(
                  sys.exc_type,
                  sys.exc_value,
                  sys.exc_traceback
            ))
            mail_admin(user_data.user.email(), msg)
            # And skip user mail.
            continue

         # Create the hits email message
         msg = mail.EmailMessage()
         msg.initialize(
            to = user_data.user.email(),
            sender = "pubcron.mailer@gmail.com",
            subject = "Recently on PubMed",
            body = "Message in HTML format.",
            html = template.render(path_to_hits, template_values))
         msg.send()


application = webapp.WSGIApplication([
  ("/send", Despatcher),
], debug=True)

def main():
   run_wsgi_app(application)

if __name__ == '__main__':
    main()
