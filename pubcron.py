# -*- coding: utf-8 -*-

import os
import re
import cgi
import wsgiref.handlers

from app_admin import UserData, term_key
import app_admin
import eUtils

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app



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
   if not re.match('^(,[0-9]{8})*$', idlist):
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
            user_data.relevant_ids = db.Text(u'')
            user_data.irrelevant_ids = db.Text(u'')
            user_data.put()

         template_values = {
            'user_data': user_data,
            'user_email': user.email(),
         }

         path = os.path.join(os.path.dirname(__file__),
               'query.html')
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
            eUtils.get_hit_count(
                  term = user_data.term,
                  email = app_admin.admail
            )
            success = True
         except (TermException, eUtils.PubMedException,
               eUtils.NoHitException):
            # Term error, PubMed error or no nit: We keep
            # 'success' as False.
            pass
         except Exception, e:
            # Something else happened: send a mail to admin.
            app_admin.mail_admin(user_data.user.email())
            pass

         user_data.term_valid = success
         user_data.put()

      self.redirect('/query.html')


class MailUpdate(webapp.RequestHandler):
   """Handle Gmail form update."""

   def get(self):
      self.response.out.write(open(os.path.join(
            os.path.dirname(__file__),
            'problem.html')
         ).read()
      )

   def post(self):
      user = users.get_current_user()
      if not user:
         # Not logged in.
         self.redirect(users.create_login_url(self.request.uri))

      data = UserData.gql('WHERE ANCESTOR IS :1 AND user = :2',
            term_key(), user)
      try:
         user_data = data[0]
      except IndexError:
         # Hacked!! To send the form, Gmail must be open
         # and the user logged in.
         return

      if not user.nickname() == self.request.get('user'):
         # Mistake: user responds to a mail addressed
         # to another user.
         return

      prev = user_data.relevant_ids + ',' + \
            user_data.irrelevant_ids
      relevant_ids = ''
      irrelevant_ids = ''

      # Process key/value pairs.
      for name in self.request.arguments():
         if name in prev + relevant_ids + irrelevant_ids:
            # Abstract already marked: skip.
            continue
         # NB: other cases are either no answer, or non
         # pmid post (like user id).
         if self.request.get(name) == 'Yes':
            relevant_ids += ',' + name
         elif self.request.get(name) == 'No':
            irrelevant_ids += ',' + name

      try:
         validate_pmid(relevant_ids + irrelevant_ids)
      except DataException:
         # Hacked!! pmids have changed before POST.
         return


      # Update the list of marked abstracts...
      user_data.relevant_ids = db.Text(
           re.sub('^,', '', user_data.relevant_ids + relevant_ids)
      )
      user_data.irrelevant_ids = db.Text(
           re.sub('^,', '', user_data.irrelevant_ids + irrelevant_ids)
      )
      # ... and put.
      user_data.put()

      template_values = {
            'user_data': user_data,
      }

      path = os.path.join(os.path.dirname(__file__),
            'feedback.html')

      self.response.out.write(
            template.render(path, template_values))



application = webapp.WSGIApplication([
  ('/query.html', MainPage),
  ('/update', UpdateTerm),
  ('/mailupdate', MailUpdate),
], debug=True)


def main():
   run_wsgi_app(application)


if __name__ == '__main__':
    main()
