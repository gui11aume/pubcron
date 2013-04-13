# -*- coding: utf-8 -*-

import os
import json
import urllib
import logging
from urllib2 import quote
from datetime import date, timedelta
from hashlib import sha1

import webapp2
from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.ext import deferred

import models
import utils
import config

import addlibdir
# Imports from the 'lib' directory.
import eUtils
import Classify

# The file 'apikey.py' is in '.gitignore'.
from apikey import apikey
ALCHEMY = 'http://access.alchemyapi.com/calls/text/TextGetRankedKeywords'

# Globals.
MAX_DATASTORE_FETCH = 100

def alchemy_keyword_query(text):
   data = urllib.urlencode({
       'keywordExtractMode': 'strict',
       'outputMode':         'json',
       'text':                text.encode('ascii', 'ignore'),
       'apikey':              apikey,
   })
   return urllib.urlopen(ALCHEMY, data).read()


class Despatcher(webapp2.RequestHandler):
   """Called by the cron scheduler. Query PubMed with all the
   saved user terms and send them a mail."""
   def get(self):
      # Check if there was anything new on PubMed yesterday.
      yesterday = date.today() - timedelta(1)
      try:
         eUtils.get_hit_count(
               term = yesterday.strftime("%Y%%2F%m%%2F%d[crdt]"),
               email = config.ADMAIL
         )
      except eUtils.PubMedException:
         return

      # Get all user data.
      all_user_data = models.UserData.all().fetch(MAX_DATASTORE_FETCH)

      for data in all_user_data:
         # Skip user if term is not valid (or empty).
         if not data.term_valid:
            continue
         try:
            deferred.defer(get_hits_and_send_mail, data)
         except Exception as e:
            logging.warn('%s: %s' % (data.user.email(), str(e)))


def get_hits_and_send_mail(data):
   """Routine to fetch user's hits and send them the results."""
   # We query PubMed for the entries created yesterday.
   # There is a bit of variability on the update time,
   # so one might miss the entries of today if they are
   # put after the cron time.
   yesterday = date.today() - timedelta(1)
   the_day_before = yesterday - timedelta(1)
   one_year_ago = yesterday - timedelta(365)

   term = str(data.term)
   term_yesterday = "("+term+")" + \
         yesterday.strftime("+AND+(%Y%%2F%m%%2F%d[crdt])")
   term_older = "("+term+")" + \
         one_year_ago.strftime("+AND+(%Y%%2F%m%%2F%d:") + \
         the_day_before.strftime("%Y%%2F%m%%2F%d[crdt])")

   # Fetch the abstracts.
   try:
      abstr_list = eUtils.fetch_abstr(
            term = term_yesterday,
            # Limit on all queries, to keep it light.
            retmax = config.RETMAX,
            email = config.ADMAIL
      )
   except NoHitException:
      return

   # Can be empty. No big deal, just return.
   if abstr_list == []: return

   user_gave_relevance_feedback = \
         utils.decrypt(data, 'relevant_docs') and \
         utils.decrypt(data, 'irrelevant_docs')

   if not user_gave_relevance_feedback:
      # No relevance feedback: set all scores to 0 and move on.
      for abstr in abstr_list:
         abstr['score'] = 0.0

   else:
      # User gave feedback: recall their data and compute scores.
      relevant_docs = utils.decrypt(data, 'relevant_docs')
      irrelevant_docs = utils.decrypt(data, 'irrelevant_docs')
      mu_corpus = utils.decrypt(data, 'mu_corpus')

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
   maxhit_exceeded = ''
   if nhits > config.MAXHITS:
      # Send the top of the sorted list and notify the user.
      maxhit_exceeded = 'Showing only the top %d.' % \
            app_admin.MAXHITS
      abstr_list = abstr_list[:config.MAXHITS]
      # User's query may also exceed app_admin.RETMAX
      # (the limit in eSearch results). Let's check that
      # too while we're at it.
      yesterdays_hit_count = eUtils.get_hit_count(
            term = term_yesterday,
            email = config.ADMAIL
      )

   ## Alchemy test.
   if data.user.email() == 'guillaume.filion@gmail.com':
      for abstr in abstr_list:
         query = json.loads(alchemy_keyword_query(abstr.get('text')))
         abstr['keywords'] = [kw['text'] for kw in  query['keywords']]


   # Make a security checksum.
   # 1. Concatenate the PMIDs.
   pmids = ''.join(sorted([a['pmid'] for a in abstr_list]))
   # 2. Add the random salt, and compute the SHA1 digest.
   checksum = sha1(pmids + data.salt).hexdigest()

   template_vals = {
      'nhits': nhits,
      'maxhit_exceeded': maxhit_exceeded,
      'uid': data.user.user_id(),
      'checksum': checksum,
      'abstr_list': abstr_list,
   }
   # Create the hits email message and send.
   msg = mail.EmailMessage()
   msg.initialize(
         to = data.user.email(),
         sender = "pubcron.mailer@gmail.com",
         subject = "Recently on PubMed",
         body = "Message in HTML format.",
         html = utils.render('mail.html', template_vals)
   )
   msg.send()
   logging.warn('mail sent to %s' % data.user.email())
   return


app = webapp2.WSGIApplication([
  ('/send', Despatcher),
])
