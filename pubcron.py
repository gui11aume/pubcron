# -*- coding: utf-8 -*-

import webapp2
from google.appengine.api import users

import utils
import models
import config

import addlibdir
# Imports from the 'lib' directory.
import tfidf
import zlib
import eUtils
import json


class TermException(Exception):
   """Exception to notify term error."""
   pass


def get_user_data(parent):
   """Make sure user is logged in and get their account data."""
   # Get user login status.
   user = users.get_current_user()
   if user is None:
      # User is not logged in... Go log in then.
      parent.redirect(users.create_login_url(parent.request.uri))
      return None
   # User is logged in.
   data = models.UserData.get_by_key_name(user.user_id())
   if data is None:
      # First time logged in. Welcome then.
      data = models.init_data(user)
   return data


def try_to_update_term(data, term):
   # Spaces cause eUtils queries to fail.
   term = term.replace(' ', '+').upper()
   # Minimal check for term inconsistencies.
   for forbidden in ['/', ' ', 'CRDT', 'CRDAT']:
      if forbidden in term: raise TermException(forbidden)
   success = False
   try:
      # If we can create the micro-corpus with the new term,
      # then do the update. Otherwise something went wrong.
      abstr_sample = eUtils.fetch_abstr(
         term = term,
         retmax = config.RETMAX,
         email = config.ADMAIL
      )
      mu_corpus = {}
      for abstr in abstr_sample:
         mu_corpus[abstr['pmid']] = tfidf.preprocess(abstr['text'])
      data.mu_corpus = zlib.compress(json.dumps(mu_corpus))
   except (eUtils.PubMedException, eUtils.NoHitException):
      # PubMed error or no nit.
      success = False
   else:
      success = True

   data.term_valid = success
   data.term = term
   data.put()
   return success

class TemplateServer(webapp2.RequestHandler):
   def get(self, query):
      if not query: query = 'index'
      template = {
         'index': 'base.html',
         'about': 'about.html',
         'FAQE':  'FAQE.html',
      }.get(query, '404.html')
      self.response.out.write(utils.render(template))


class QueryPageServer(webapp2.RequestHandler):
   def get(self):
      data = get_user_data(self)
      self.response.out.write(utils.render(
         'query.html',
         {'data':data}
      ))


class QueryUpdateServer(webapp2.RequestHandler):
   def post(self):
      data = get_user_data(self)
      updated = try_to_update_term(data, self.request.get('term'))
      self.redirect('/query')


app = webapp2.WSGIApplication([
   ('/query', QueryPageServer),
   ('/update', QueryUpdateServer),
   ('/(.*)', TemplateServer),
])
