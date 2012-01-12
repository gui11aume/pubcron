# -*- coding: utf-8 -*-

import os
try:
   import json
except ImportError:
   import simplejson as json
import datetime
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

      # Debug mode: /send?debug=your.name@example.com
      debug = self.request.get('debug', False)
      # Path to the mail html template.
      path_to_hits = os.path.join(os.path.dirname(__file__),
            'hits.html')

      # Yesterday, the day before and one year ago.
      # We query PubMed for the entries created yesterday.
      # There is a bit of variability on the update time,
      # so one might miss the entries of today if they are
      # put after the cron time.
      yesterday = datetime.datetime.today() + \
            datetime.timedelta(days = -1)
      the_day_before = yesterday + datetime.timedelta(days = -1)
      one_year_ago = datetime.datetime.today() + \
            datetime.timedelta(days = -365)

      # Check if there was anything new on PubMed yesterday.
      try:
         n_crdt = eUtils.get_hit_count(
               term = yesterday.strftime("%Y%%2F%m%%2F%d[crdt]"),
               email = app_admin.ADMAIL
         )
      except eUtils.PubMedException, e:
         # If PubMed returns a 'PhraseNotFound' with yesterday's date
         # nothing is happening: just notify admin.
         if e.args == ([([u'PhraseNotFound'],
                       yesterday.strftime("%Y/%m/%d[crdt]"))],):
            app_admin.mail_admin(app_admin.ADMAIL, 'No PubMed update.')
         # Else send the full error trace.
         else:
            app_admin.mail_admin(app_admin.ADMAIL)
         # In both cases see you tomorrow!
         return


      # Get all user data.
      data = app_admin.UserData.gql(
                  "WHERE ANCESTOR IS :1",
                  app_admin.user_key()
             )

      for user_data in data:

         term = str(user_data.term)

         # While debugging, skip all users except target.
         elif user_data.user.email() != debug:
            continue

         # Skip user if term is not valid (or empty incidentally).
         if not user_data.term_valid:
            continue


         term_yesterday = "("+term+")" + \
               yesterday.strftime("+AND+(%Y%%2F%m%%2F%d[crdt])")

         term_older = "("+term+")" + \
               one_year_ago.strftime("+AND+(%Y%%2F%m%%2F%d:") + \
               the_day_before.strftime("%Y%%2F%m%%2F%d[crdt])")

         # Fetch the abstracts.
         try:
            abstr_list = eUtils.fetch_abstr(
                  term = term_today,
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
               todays_hit_count = eUtils.get_hit_count(
                     term = term_recent,
                     email = app_admin.ADMAIL
               )
               retmax_exceeded = True if \
                  todays_hit_count > app_admin.RETMAX else False
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
