import os
import re
import cgi
import datetime
import urllib
import wsgiref.handlers

import eUtils

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


class UserData(db.Model):
   """Store user term query and date lat run."""
   user = db.UserProperty()
   term = db.StringProperty()
   term_valid = db.BooleanProperty()
   last_run = db.DateTimeProperty()
   relevant_ids = db.TextProperty()
   irrelevant_ids = db.TextProperty()
   positive_terms = db.TextProperty()
   negative_terms = db.TextProperty()

def term_key():
   """Construct a datastore key for a Term entity."""
   return db.Key.from_path('Term', '1')

class UpdateException(Exception):
   pass

class TermException(UpdateException):
   pass

class DataException(UpdateException):
   pass

def clean(term):
   return term.replace(' ', '+')

def validate_term(term):
   term = term.upper()
   if '/' in term:
      raise TermException('/')
   if ' ' in term:
      raise TermException(' ')
   if 'CRDT' in term or 'CRDAT' in term:
      raise TermException('CRDT')

def validate_pmid(idlist):
   """List of PMIDs consist of 8 digits separated by ':'."""
   if not re.match('([0-9]{8}:)*$', idlist):
      raise DataException



class MainPage(webapp.RequestHandler):
   def get(self):

      # Already logged in?
      user = users.get_current_user()

      if user:
         # From here the user is logged in as user.
         data = UserData.gql('WHERE ANCESTOR IS :1 AND user = :2',
               term_key(), user)
         try:
            user_data = data[0]
         except IndexError:
            # First user visit: create user data.
            user_data = UserData(term_key())
            user_data.user = user
            user_data.relevant_ids = db.Text(u':')
            user_data.irrelevant_ids = db.Text(u':')
            user_data.positive_terms = db.Text(u':')
            user_data.negative_terms = db.Text(u':')
            user_data.put()

         template_values = {
            'user_data': user_data,
            'user_email': user.email(),
         }

         path = os.path.join(os.path.dirname(__file__),
               'index.html')
         self.response.out.write(
               template.render(path, template_values))

      else:
         # Not logged in... Go log in then.
         self.redirect(users.create_login_url(self.request.uri))


class UpdateTerm(webapp.RequestHandler):
   """Handle user term update."""
   def post(self):
      user = users.get_current_user()
      if user:
         data = UserData.gql('WHERE ANCESTOR IS :1 AND user = :2',
               term_key(), user)

         user_data = data[0]

         # Update term.
         term = clean(self.request.get('term'))
         user_data.term = cgi.escape(term)

         # Check if term is OK.
         success = False
         try:
            validate_term(user_data.term)
            eUtils.robust_eSearch_query(user_data.term)
            success = True
         except eUtils.RetMaxExceeded:
            # Too many hits... That's good.
            success = True
         except (TermException, eUtils.PubMedException,
               eUtils.NoHitException):
            # Term error, PubMed error or no nit: We keep
            # 'success' as False.
            pass 
         except Exception:
            # Something else happened.
            #TODO: issue a warning.
            pass

         user_data.term_valid = success
         user_data.put()

      self.redirect('/')


class MailUpdate(webapp.RequestHandler):
   """Handle Gmail form update."""
   def post(self):
      user = users.get_current_user()
      data = UserData.gql('WHERE ANCESTOR IS :1 AND user = :2',
            term_key(), user)
      try:
         user_data = data[0]
      except IndexError:
         # Hacked: to send the form, Gmail must be open
         # and the user logged in.
         return

      if not user.nickname() == self.request.get('user'):
         # Mistake: user responds to a mail addressed
         # to another user.
         return

      prev = user_data.relevant_ids + \
            user_data.irrelevant_ids
      relevant_ids = ''
      irrelevant_ids = ''
      positive_terms = ''
      negative_terms = ''

      # Process the key/value terms. The keys consist of
      # pmid:title, they are split before processing.
      for name in self.request.arguments():
         if not self.request.get(name) in ('Yes', 'No'):
            # Not a Yes/No answer (e.g. user, or NA): skip.
            continue
         (pmid, terms) = name.split(':', 1)
         if pmid in prev + relevant_ids + irrelevant_ids:
            # Abstract already marked: skip.
            continue
         if self.request.get(name) == 'Yes':
            relevant_ids += pmid +  ':'
            positive_terms += terms + ':'
         elif self.request.get(name) == 'No':
            irrelevant_ids += pmid + ':'
            negative_terms += terms + ':'

      try:
         validate_pmid(relevant_ids + irrelevant_ids)
      except DataException:
         # Hacked: pmids have changed before POST.
         return


      # Update the positive and negative words...
      user_data.positive_terms = db.Text(
            user_data.positive_terms + positive_terms
         )
      user_data.negative_terms = db.Text(
            user_data.negative_terms + negative_terms
         )
      # ... the list of marked abstracts...
      user_data.relevant_ids = db.Text(
            user_data.relevant_ids + relevant_ids
         )
      user_data.irrelevant_ids = db.Text(
            user_data.irrelevant_ids + irrelevant_ids
         )
      # ... and push.
      user_data.put()


application = webapp.WSGIApplication([
  ('/', MainPage),
  ('/update', UpdateTerm),
  ('/mailupdate', MailUpdate),
], debug=True)


def main():
   run_wsgi_app(application)


if __name__ == '__main__':
    main()
