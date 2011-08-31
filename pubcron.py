import os
import cgi
import datetime
import urllib
import wsgiref.handlers

import PubMed

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.api import mail
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


class MainPage(webapp.RequestHandler):
   def get(self):
      xmlabstr_list = PubMed.query()
      template_values = {
         'abstr_list': xmlabstr_list
      }

      path = os.path.join(os.path.dirname(__file__), 'index.html')
      self.response.out.write(template.render(path, template_values))


application = webapp.WSGIApplication([
  ('/', MainPage),
], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()
