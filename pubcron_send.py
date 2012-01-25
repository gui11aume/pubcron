# -*- coding: utf-8 -*-

import os
try:
   import json
except ImportError:
   import simplejson as json
from datetime import date, timedelta
from hashlib import sha1

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
      # Check if there was anything new on PubMed yesterday.
      yesterday = date.today() - timedelta(1)
      try:
         eUtils.get_hit_count(
               term = yesterday.strftime("%Y%%2F%m%%2F%d[crdt]"),
               email = app_admin.ADMAIL
         )
      except eUtils.PubMedException, e:
         app_admin.mail_admin(app_admin.ADMAIL)
         return

      # Get all user data.
      data = app_admin.UserData.gql(
                "WHERE ANCESTOR IS :1",
                app_admin.user_key()
      )

      # Debug mode: /send?debug=your.name@example.com
      debug = self.request.get('debug', False)

      for user_data in data:
         # If debugging, skip all users except target.
         if debug and user_data.user.email() != debug:
            continue
         # Skip user if term is not valid (or empty incidentally).
         if not user_data.term_valid:
            continue

         try:
            get_hits_and_send_mail(user_data)
         except eUtils.NoHitException:
            # No hit today. Better luck tomorrow :-)
            continue
         except Exception, e:
            # For other exceptions (including PubMedExceptions), send
            # a mail to amdin.
            app_admin.mail_admin(user_data.user.email())
            # And see ou tomorrow.
            continue


def get_hits_and_send_mail(user_data):
   """Routine to fetch user's hits and send them the results."""

   # Yesterday, the day before and one year ago.
   # We query PubMed for the entries created yesterday.
   # There is a bit of variability on the update time,
   # so one might miss the entries of today if they are
   # put after the cron time.
   yesterday = date.today - timedelta(1)
   the_day_before = yesterday - timedelta(1)
   one_year_ago = yesterday - timedelta(365)

   term = str(user_data.term)

   term_yesterday = "("+term+")" + \
         yesterday.strftime("+AND+(%Y%%2F%m%%2F%d[crdt])")

   term_older = "("+term+")" + \
         one_year_ago.strftime("+AND+(%Y%%2F%m%%2F%d:") + \
         the_day_before.strftime("%Y%%2F%m%%2F%d[crdt])")

   # Fetch the abstracts.
   abstr_list = eUtils.fetch_abstr(
         term = term_yesterday,
         # Limit on all queries, to keep it light.
         retmax = app_admin.RETMAX,
         email = app_admin.ADMAIL
   )

   user_gave_relevance_feedback = \
         app_admin.decrypt(user_data, 'relevant_docs') and \
         app_admin.decrypt(user_data, 'irrelevant_docs')

   if not user_gave_relevance_feedback:
      # No relevance feedback: set all scores to 0 and move on.
      for abstr in abstr_list:
         abstr['score'] = 0.0

   else:
      # User gave feedback: recall their data and compute scores.
      relevant_docs = app_admin.decrypt(user_data, 'relevant_docs')
      irrelevant_docs = app_admin.decrypt(user_data, 'irrelevant_docs')
      mu_corpus = app_admin.decrypt(user_data, 'mu_corpus')

      # Write the scores in place and sort.
      Classify.update_score_inplace(
            abstr_list,
            relevant_docs,
            irrelevant_docs,
            mu_corpus
      )

      abstr_list = sorted(
            abstr_list,
            key = lambda x: x.get('score', 0.0),
            reverse = True
      )

      # Set a limit on hit number.
      nhits = len(abstr_list)
      if nhits > app_admin.MAXHITS:
      # Send the top of the sorted list and notify the user.
      maxhit_exceeded = 'Showing only the top %d.' % \
            app_admin.MAXHITS
      abstr_list = abstr_list[:app_admin.MAXHITS]
      # User's query may also exceed app_admin.RETMAX
      # (the limit in eSearch results). Let's check that
      # too while we're at it.
      yesterdays_hit_count = eUtils.get_hit_count(
            term = term_yesterday,
            email = app_admin.ADMAIL
      )
      retmax_exceeded = True if \
            yesterdays_hit_count > app_admin.RETMAX else False
   else:
      maxhit_exceeded = ''
      retmax_exceeded = False

   # Make a security checksum.
   # 1. Concatenate the PMIDs.
   pmids = ''.join(sorted([a['pmid'] for a in abstr_list]))
   # 2. Add the random salt, and compute the SHA1 digest.
   checksum = sha1(pmids + user_data.salt).hexdigest()

   template_values = {
         'nhits': nhits,
         'maxhit_exceeded': maxhit_exceeded,
         'retmax_exceeded': retmax_exceeded,
         'uid': user_data.uid,
         'checksum': checksum,
         'abstr_list': abstr_list,
   }
   # Path to the mail html template.
   path_to_hits = os.path.join(os.path.dirname(__file__), 'hits.html')

   # Create the hits email message and send.
   msg = mail.EmailMessage()
   msg.initialize(
         to = user_data.user.email(),
         sender = "pubcron.mailer@gmail.com",
         subject = "Recently on PubMed",
         body = "Message in HTML format.",
         html = template.render(path_to_hits, template_values))
   msg.send()

   # Voila.
   return


application = webapp.WSGIApplication([
  ("/send", Despatcher),
], debug=True)

def main():
   run_wsgi_app(application)

if __name__ == '__main__':
    main()
