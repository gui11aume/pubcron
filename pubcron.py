# -*- coding: utf-8 -*-

import webapp2
from google.appengine.api import users

import utils
import models


class TermException(Exception):
   """Exception to notify term error."""
   pass


def get_user_data(parent):
   """Make sure user is logged in and get their account data."""
   # Get user login status.
   user = users.get_current_user()
   if user is None:
      # User is not logged in... Go log in then.
      parent.redirect(users.create_login_url(parent.request.uri))
      return None
   # User is logged in.
   data = models.UserData.get_by_key_name(user.user_id())
   if data is None:
      # First time logged in. Welcome then.
      data = models.init_data(user)
   return data


class TemplateServer(webapp2.RequestHandler):
   def get(self, query):
      if not query: query = 'index'
      template = {
         'index': 'base.html',
         'about': 'about.html',
         'FAQE':  'FAQE.html',
      }.get(query, '404.html')
      self.response.out.write(utils.render(template))


class QueryPageServer(webapp2.RequestHandler):
   def get(self):
      data = get_user_data(self)
      self.response.out.write(utils.render(
         'query.html',
         {'data':data}
      ))


class QueryUpdateServer(webapp2.RequestHandler):
   def post(self):
      data = get_user_data(self)
      updated = utils.try_to_update_term(data, self.request.get('term'))
      self.redirect('/query')


app = webapp2.WSGIApplication([
   ('/query', QueryPageServer),
   ('/update', QueryUpdateServer),
   ('/(.*)', TemplateServer),
])
