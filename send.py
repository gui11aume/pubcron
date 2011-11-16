# -*- coding: utf-8 -*-

import os
import datetime


from app_admin import UserData, term_key
import app_admin
import eUtils
import Classify


from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.api import mail
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


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
                  retmax = app_admin.RETMAX,
                  email = app_admin.admail
            )

            # Ensure user gave feedback before computing scores.
            if user_data.relevant_ids and user_data.irrelevant_ids:

               # Recall relevant and irrelevant abstracts.
               Abstr_relevant = eUtils.fetch_ids(
                     user_data.relevant_ids.split(','),
                     retmax = app_admin.RETMAX,
                     email = admail
               )
               Abstr_irrelevant = eUtils.fetch_ids(
                     user_data.irrelevant_ids.split(','),
                     retmax = app_admin.RETMAX,
                     email = admail
               )

               # Get a pseudo random micro-corpus of older hits with
               # same term (to avoid hit duplication), for tf-idf.
               # This is useful when little feedback is available,
               # or when the query changed.
               micro_corpus = eUtils.fetch_Abstr(
                     term = term_older,
                     retmax = app_admin.RETMAX,
                     email = admail
               )

               # Write the scores in place and sort.
               Classify.update_score_inplace(
                     Abstr_list,
                     Abstr_relevant,
                     Abstr_irrelevant,
                     micro_corpus
               )

               Abstr_list = sorted(Abstr_list, reverse=True)

            else:
               # No relevance feedback.
               for abstr in Abstr_list:
                  abstr.score = 0.0

            # Set a limit on hit number.
            nhits = len(Abstr_list)
            if nhits > app_admin.MAXHITS:
               # Send the top of the sorted list and notify the user.
               maxhit_exceeded = 'Showing only the top %d.' % \
                     app_admin.MAXHITS
               Abstr_list = Abstr_list[:app_admin.MAXHITS]
               # User's query may also exceed app_admin.RETMAX
               # (the limit in eSearch results). Let's check that
               # too while we're at it.
               todays_hit_count = eUtils.get_hit_count(
                     term = term_recent,
                     email = app_admin.admail
               )
               if todays_hit_count > app_admin.RETMAX:
                  retmax_exceeded = \
                  """Important note: the number of hits returned
                  by your query exceeded the limit of abstracts that
                  PubCron requests from PubMed. As a results, some
                  hits were ignored. Enter a more specific query term
                  if this message appears regularly."""
            else:
               maxhit_exceeded = ''
               retmax_exceeded = ''

            template_values = {
               'nhits': nhits,
               'maxhit_exceeded': maxhit_exceeded,
               'retmax_exceeded': retmax_exceeded,
               'user': user_data.user.nickname(),
               'Abstr_list': Abstr_list
            }

         except eUtils.NoHitException:
            # No hit today. Better luck tomorrow :-)
            continue
         except Exception, e:
            # For other exceptions (including PubMedExceptions), send
            # a mail to amdin.
            app_admin.mail_admin(user_data.user.email())
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
