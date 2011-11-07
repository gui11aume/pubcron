# -*- coding: utf-8 -*-

import os

import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class Home(webapp.RequestHandler):

   def get(self):
      self.response.out.write(open(os.path.join(
           os.path.dirname(__file__),
           'index.html')
      ).read()
   )

class Help(webapp.RequestHandler):

   def get(self):
      self.response.out.write(open(os.path.join(
           os.path.dirname(__file__),
           'help.html')
      ).read()
   )

class NotFound(webapp.RequestHandler):
   """All other pages are not found."""

   def get(self):
      self.response.out.write(open(os.path.join(
           os.path.dirname(__file__),
           'notfound.html')
      ).read()
   )

application = webapp.WSGIApplication([
   ('/', Home),
   ('/index.html?', Home),
   ('/help.html?', Help),
   ('/.*', NotFound)
], debug=True)


def main():
   run_wsgi_app(application)


if __name__ == '__main__':
   main()
