import os
import cgi
import datetime
import urllib
import wsgiref.handlers

import eUtils
import PubMed

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.api import mail
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from xml.dom.minidom import parse, parseString

class MainPage(webapp.RequestHandler):
   def get(self):
      try:
         abstr_list = PubMed.query()
         template_values = {
            'abstr_list': abstr_list
         }
         path = os.path.join(os.path.dirname(__file__), 'index.html')
      except eUtils.PubMedException, error:
         template_values = {
            'pair_list': error.pair_list
         }
         path = os.path.join(os.path.dirname(__file__), 'error.html')
      except eUtils.NoHitException:
         pass
      msg = mail.EmailMessage()
      msg.initialize(to="rickylim19@gmail.com",
         sender="guillaume.filion@gmail.com",
         subject="Hi there", body="Here is a message",
         html=template.render(path, template_values))
      msg.send()
  
application = webapp.WSGIApplication([
  ('/', MainPage),
], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()
