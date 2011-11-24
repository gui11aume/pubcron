# -*- coding: utf-8 -*-

import os

import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

class Home(webapp.RequestHandler):

   def get(self):
      dot = os.path.dirname(__file__)
      template_path = os.path.join(dot, 'pubcron_template.html')
      content_path = os.path.join(dot, 'content', 'index_content.html')

      template_values = {
         'page_title': 'Welcome to PubCron',
         'page_content': open(content_path).read()
      }
      self.response.out.write(
         template.render(template_path, template_values)
      )

class Help(webapp.RequestHandler):

   def get(self):
      dot = os.path.dirname(__file__)
      template_path = os.path.join(dot, 'pubcron_template.html')
      content_path = os.path.join(dot, 'content', 'help_content.html')

      template_values = {
         'page_title': 'PubCron help',
         'page_content': open(content_path).read()
      }
      self.response.out.write(
         template.render(template_path, template_values)
      )

class FAQE(webapp.RequestHandler):

   def get(self):
      dot = os.path.dirname(__file__)
      template_path = os.path.join(dot, 'pubcron_template.html')
      content_path = os.path.join(dot, 'content', 'FAQE_content.html')

      template_values = {
         'page_title': 'PubCron FAQ(E)',
         'page_content': open(content_path).read()
      }
      self.response.out.write(
         template.render(template_path, template_values)
      )

class NotFound(webapp.RequestHandler):
   """All other pages are not found."""

   def get(self):
      dot = os.path.dirname(__file__)
      template_path = os.path.join(dot, 'pubcron_template.html')
      content_path = os.path.join(dot, 'content', 'notfound_content.html')

      template_values = {
         'page_title': 'Page not found',
         'page_content': open(content_path).read()
      }
      self.response.out.write(
         template.render(template_path, template_values)
      )


application = webapp.WSGIApplication([
   ('/', Home),
   ('/index.html?', Home),
   ('/help.html?', Help),
   ('/FAQE.html?', FAQE),
   ('/.*', NotFound)
], debug=True)


def main():
   run_wsgi_app(application)


if __name__ == '__main__':
   main()
