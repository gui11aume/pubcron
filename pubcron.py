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
   marked_abstracts = db.Text()

def term_key():
   """Construct a datastore key for a Term entity."""
   return db.Key.from_path("Term", "1")

class UpdateException(Exception):
   pass

class TermException(UpdateException):
   pass

class DataException(UpdateException):
   pass

def clean(term):
   return term.replace(" ", "+")

def validate_term(term):
   term = term.upper()
   if term.find("/") > -1:
      raise TermException("/")
   if term.find(" ") > -1:
      raise TermException(" ")
   if term.find("CRDT") > -1 or term.find("CRDAT") > -1:
      raise TermException("CRDT")

def validate_pmid(id):
   if not re.match('[0-9]+$', id):
      raise DataException


class MainPage(webapp.RequestHandler):
   def get(self):

      # Already logged in?
      user = users.get_current_user()

      if user:
         # From here the user is logged in as user.
         data = UserData.gql("WHERE ANCESTOR IS :1 AND user = :2",
               term_key(), user)
         try:
            user_data = data[0]
         except IndexError:
            # First user visit: create user data.
            user_data = UserData(term_key())
            user_data.user = user
            user_data.put()
   
         template_values = {
            "user_data": user_data,
            "user_email": user.email(),
            "logout_url": users.create_logout_url(self.request.uri),
         }

         path = os.path.join(os.path.dirname(__file__), 'index.html')
         self.response.out.write(template.render(path, template_values))

      else:
         # Not logged in... Go log in then.
         self.redirect(users.create_login_url(self.request.uri))
   

class UpdateTerm(webapp.RequestHandler):
   """Handle user term update."""
   def post(self):
      user = users.get_current_user()
      if user:
         data = UserData.gql("WHERE ANCESTOR IS :1 AND user = :2",
               term_key(), user)

         user_data = data[0]

         # Update term.
         term = clean(self.request.get("term"))
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

      self.redirect("/")

class MailUpdate(webapp.RequestHandler):
   """Handle Gmail form update."""
   def post(self):
      try:
         pmid = self.request.get("pmid")
         validate_pmid(pmid)
      except DataException:
         # Hacked!
         return

      user = users.get_current_user()
      data = UserData.gql("WHERE ANCESTOR IS :1 AND user = :2",
            term_key(), user)

      try:
         user_data = data[0]
      except IndexError:
         # Hacked!
         return

      if not user.nickname() == self.request.get("user"):
         # Hacked!
         return

      if not re.search(pmid, user_data.marked_abstracts):
         user_data.marked_abstracts += ":" + pmid
         user_data.put()

      self.response.out.write("Feature under development")


application = webapp.WSGIApplication([
  ("/", MainPage),
  ("/update", UpdateTerm),
  ("/mailupdate", MailUpdate),
], debug=True)


def main():
   run_wsgi_app(application)


if __name__ == '__main__':
    main()
