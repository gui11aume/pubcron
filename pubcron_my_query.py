# -*- coding: utf-8 -*-

import os
import re
import cgi
try:
   import json
except ImportError:
   import simplejson as json
from hashlib import sha1

import app_admin
import eUtils
import tfidf

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


class TermException():
   pass


class QueryPage(webapp.RequestHandler):
   """Handle requests to user's personal query page."""

   def get(self):

      # Get user login status.
      user = users.get_current_user()

      if not user:
         # User is not logged in... Go log in then.
         self.redirect(users.create_login_url(self.request.uri))

      else:
         # User is logged in.
         data = app_admin.UserData.gql(
                     'WHERE ANCESTOR IS :1 AND user = :2',
                     app_admin.user_key(),
                     user
                )
         
         very_first_user_login = data.count() == 0
         if very_first_user_login:
            # Grab a new instance of user data.
            user_data = app_admin.init_data(user)
         else:
            user_data = data[0]

         dot = os.path.dirname(__file__)

         # First fill in the content itself (not the HTML page).
         content_values = {
            'user_data': user_data,
            'user_email': user.email(),
         }

         content_path = os.path.join(dot, 'content', 'query_content.html')
         content = template.render(content_path, content_values)

         # Now fill in the HTML page...
         template_path = os.path.join(dot, 'pubcron_template.html')
         template_values = {
            'page_title': 'PubCron query',
            'page_content': content,
         }

         # ... and send!
         self.response.out.write(
               template.render(template_path, template_values)
         )



class UpdateTerm(webapp.RequestHandler):
   """Handle user term update."""

   def interpret(self, term):
      """Perform minimal interpretation on the user-submitted term
      to ease the upate process."""
      
      # Spaces cause eUtils queries to fail.
      return term.replace(' ', '+')


   def validate_term(self, term):
      """Minimal check for term inconsistencies."""

      term = term.upper()
      if '/' in term:
         raise TermException('/')
      if ' ' in term:
         raise TermException(' ')
      if 'CRDT' in term or 'CRDAT' in term:
         raise TermException('CRDT')


   def post(self):

      # Get user login status
      user = users.get_current_user()

      if not user:
         # User is not logged in (Why? You need to be logged in to
         # issue an update request). Redirect to the personal query
         # page -- which will redirect to login page (redirecting
         # here after login would erase the POST arguments).
         self.redirect('/query.html')

      else:
         # User is logged in.
         data = app_admin.UserData.gql(
                     'WHERE ANCESTOR IS :1 AND user = :2',
                     app_admin.user_key(),
                     user
                )
         user_data = data[0]

         # Update user's query term.
         term = self.interpret(self.request.get('term'))
         user_data.term = cgi.escape(term)

         # Check if term is OK.
         success = False
         try:
            self.validate_term(user_data.term)
            # Proof-in-the-pudding approach: if we can create the micro-
            # corpus of the new term, then it is OK. Otherwise something
            # is wrong.
            abstr_sample = eUtils.fetch_abstr(
                  term = user_data.term,
                  retmax = app_admin.RETMAX,
                  email = app_admin.ADMAIL
            )
            mu_corpus = {}
            for abstr in abstr_sample:
               mu_corpus[abstr['pmid']] = tfidf.preprocess(abstr['text'])
            user_data.mu_corpus = json.dumps(mu_corpus)
            success = True
         except (TermException, eUtils.PubMedException,
               eUtils.NoHitException):
            # Term error, PubMed error or no nit: We keep
            # 'success' as False.
            pass
         except Exception, e:
            # Something else happened: send the error report to admin
            # (and keep 'success' as False).
            app_admin.mail_admin(user_data.user.email())
            pass

         user_data.term_valid = success
         user_data.put()

      self.redirect('/query.html')



application = webapp.WSGIApplication([
  ('/query.html', QueryPage),
  ('/update', UpdateTerm),
], debug=True)


def main():
   run_wsgi_app(application)


if __name__ == '__main__':
    main()
