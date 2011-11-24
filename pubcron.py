# -*- coding: utf-8 -*-

import os
import re
import cgi
import wsgiref.handlers
from hashlib import sha1

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



class Query(webapp.RequestHandler):
   def get(self):
      # Already logged in?
      user = users.get_current_user()

      if user:
         # From here the user is logged in as user.
         data = app_admin.UserData.gql('WHERE ANCESTOR IS :1 AND user = :2',
               app_admin.term_key(), user)
         try:
            user_data = data[0]
         except IndexError:
            # First user visit: create user data.
            user_data = app_admin.init_data(user)

         dot = os.path.dirname(__file__)

         # First fill in the content.
         content_values = {
            'user_data': user_data,
            'user_email': user.email(),
         }

         content_path = os.path.join(dot, 'content', 'query_content.html')
         content = template.render(content_path, content_values)

         # Now send the page.
         template_path = os.path.join(dot, 'pubcron_template.html')
         template_values = {
            'page_title': 'PubCron query',
            'page_content': content,
         }

         self.response.out.write(
               template.render(template_path, template_values)
         )

      else:
         # Not logged in... Go log in then.
         self.redirect(users.create_login_url(self.request.uri))


class UpdateTerm(webapp.RequestHandler):
   """Handle user term update."""
   def post(self):
      user = users.get_current_user()
      if user:
         data = app_admin.UserData.gql(
               'WHERE ANCESTOR IS :1 AND user = :2',
               app_admin.term_key(), user
         )

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

   def validate_request(self, user_data):
      # get PMIDs of abstracts in the mail.
      pmids = ''.join(sorted([pmid for pmid in self.request.arguments() \
            if re.match('[0-9]{8}$', pmid)]))
      # Add a bit of random salt.
      checksum = sha1(pmids + user_data.salt).hexdigest()

      return checksum == self.request.get('checksum')


   def post(self):
      # Who is it? Get it from the POST parameters.
      uid = self.request.get('uid')

      data = app_admin.UserData.gql(
            'WHERE ANCESTOR IS :1 AND uid = :2',
            app_admin.term_key(), uid
      )
      try:
         user_data = data[0]
      except IndexError:
         # Wrong uid (hacked?!!): good-bye.
         self.response.out.write(uid)
         return

      # Check that user responds to mail.
      checksum = self.validate_request(user_data)
      if not self.request.get('checksum'):
         # Invalid post paramters (hacked?!!): good-bye.
         return
      
      # Sanity checks are finished. Do the update.
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
         # pmid post (like uid or checksum).
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

      # Now reassure the user.
      dot = os.path.dirname(__file__)
      template_path = os.path.join(dot, 'pubcron_template.html')
      content_path = os.path.join(dot, 'content', 'feedback_content.html')

      template_values = {
         'page_title': 'PubCron feedback',
         'page_content': open(content_path).read(),
      }
      self.response.out.write(
         template.render(template_path, template_values)
      )



application = webapp.WSGIApplication([
  ('/query.html', Query),
  ('/update', UpdateTerm),
  ('/mailupdate', MailUpdate),
], debug=True)


def main():
   run_wsgi_app(application)


if __name__ == '__main__':
    main()
