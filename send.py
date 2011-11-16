# -*- coding: utf-8 -*-

import os
import sys
import datetime
import traceback

import eUtils
import Classify

from pubcron import UserData, term_key

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# ------------------------------------------------------------------------
RETMAX = 200
admail = 'pubcron.mailer@gmail.com'
# ------------------------------------------------------------------------


def mail_admin(useremail, msg):
   mail.send_mail(
         admail,
         admail,
         "Pubcron mail report",
         "%s:\n%s" % (useremail, msg)
   )

class Despatcher(webapp.RequestHandler):
   """Called by the cron scheduler. Query PubMed with all the
   saved user terms and send them a mail."""

   def get(self):

      # Debug mode: /send?debug=your.name@example.com
      debug = self.request.get('debug', False)

      # Path to the mail html template.
      path_to_hits = os.path.join(os.path.dirname(__file__),
            'hits.html')

      # Get all users data.
      data = UserData.gql("WHERE ANCESTOR IS :1", term_key())

      for user_data in data:

         term = str(user_data.term)
         last_run = user_data.last_run

         # Update last time run (except when debugging).
         if not debug:
            user_data.last_run = datetime.datetime.now()
            user_data.put()

         # While debugging, skip all users except target.
         elif user_data.user.email() != debug:
            continue

         # Skip user if term is not valid (or empty incidentally).
         if not user_data.term_valid:
            continue


         yesterday = datetime.datetime.today() + \
               datetime.timedelta(days = -1)
         day_before = yesterday+ datetime.timedelta(days = -1)
         one_year_ago = datetime.datetime.today() + \
               datetime.timedelta(days = -365)

         date_from = last_run or yesterday
         date_to = max(yesterday, date_from)

         term_recent = "("+term+")" + \
               date_from.strftime("+AND+(%Y%%2F%m%%2F%d:") + \
               date_to.strftime("%Y%%2F%m%%2F%d[crdt])")

         term_older = "("+term+")" + \
               one_year_ago.strftime("+AND+(%Y%%2F%m%%2F%d:") + \
               day_before.strftime("%Y%%2F%m%%2F%d[crdt])")

         # Fetch the abstracts.
         try:
            Abstr_list = eUtils.fetch_Abstr(
                  term = term_recent,
                  # Limit on all queries, to keep it light.
                  retmax = RETMAX,
                  email = admail
            )

            # Ensure user gave feedback before computing scores.
            if user_data.relevant_ids and user_data.irrelevant_ids:

               # Recall relevant and irrelevant abstracts.
               Abstr_relevant = eUtils.fetch_ids(
                     user_data.relevant_ids.split(','),
                     retmax = RETMAX,
                     email = admail
               )
               Abstr_irrelevant = eUtils.fetch_ids(
                     user_data.irrelevant_ids.split(','),
                     retmax = RETMAX,
                     email = admail
               )

               # Get a pseudo random micro-corpus of older hits with
               # same term (to avoid hit duplication), for tf-idf.
               # This is useful when little feedback is available,
               # or when the query changed.
               micro_corpus = eUtils.fetch_Abstr(
                     term = term_older,
                     retmax = RETMAX,
                     email = admail
               )

               # Write the scores in place.
               Classify.update_score_inplace(
                     Abstr_list,
                     Abstr_relevant,
                     Abstr_irrelevant,
                     micro_corpus
               )

            else:
               # No relevance feedback.
               for abstr in Abstr_list:
                  abstr.score = 0.0

            template_values = {
               'nhits': len(Abstr_list),
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
