# -*- coding: utf-8 -*-
"""
For some reason I cannot access the remote API and the Google
console issues an error. I used this script on April 13 2013
to migrate the user data of the app.
"""

import logging
import webapp2

from google.appengine.api import users

import utils
import models
import config

class Migrate(webapp2.RequestHandler):
   def get(self):
      all_user_data = models.UserData.all().fetch(100)
      for data in all_user_data:
         try:
            newdata = models.UserData(
               key_name = data.user.user_id(),
               user = data.user,
               salt = data.salt,
               mu_corpus = data.mu_corpus,
               relevant_docs = data.relevant_docs,
               irrelevant_docs = data.irrelevant_docs,
               term = data.term,
               term_valid = data.term_valid,
               # That line was useless (mistake).
               last_run = data.last_run
            )
            # Save to the datastore and return.
            newdata.put()
         except Exception as e:
            logging.warn('%s: %s' % (data.user.email(), str(e)))
         else:
            logging.warn('%s: %s' % (data.user.email(), 'successful'))

      self.response.out.write('done')

app = webapp2.WSGIApplication([
   ('/migrate', Migrate),
])
