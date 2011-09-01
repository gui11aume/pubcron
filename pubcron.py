import os
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
   last_run = db.DateTimeProperty()

def term_key():
   """Construct a datastore key for a Term entity."""
   return db.Key.from_path("Term", "1")

class TermException(Exception):
   pass

def validate(term):
   if term.upper().find("CRDT") > -1:
      raise TermException("CRDT")
   if term.find("/") > -1:
      raise TermException("/")


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
         # Go log in.
         self.redirect(users.create_login_url(self.request.uri))
   
class UpdateTerm(webapp.RequestHandler):
   def post(self):

      user = users.get_current_user()
      if user:
         data = UserData.gql("WHERE ANCESTOR IS :1 AND user = :2",
               term_key(), user)

         user_data = data[0]

         term = self.request.get("term")
         # TODO:
         # Validation is carried out by JavaScript.
         # If this fails, the user is probably trying to hack.
         validate(term)

         # Update term.
         user_data.term = cgi.escape(term)
         user_data.put()

      self.redirect("/")
         

  
application = webapp.WSGIApplication([
  ("/", MainPage),
  ("/update", UpdateTerm),
], debug=True)


def main():
   run_wsgi_app(application)


if __name__ == '__main__':
    main()
