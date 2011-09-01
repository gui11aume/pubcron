import os
import datetime
import eUtils

from pubcron import UserData, term_key

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

class Sender(webapp.RequestHandler):
   """Called by the cron scheduler. Query PubMed with all the
   saved user terms and send them a mail."""

   def get(self):

      path = None
      subject = None

      # Get all user data.
      data = UserData.gql("WHERE ANCESTOR IS :1", term_key())

      for user_data in data:
         term = str(user_data.term)
         yesterday = datetime.datetime.today() + datetime.timedelta(-1)
         date_from = user_data.last_run or yesterday
         date_to = yesterday
   
         # Update last time run.
         user_data.last_run = datetime.datetime.now()
         user_data.put()

         # Fetch the abstracts.
         try:
            (abstr_list, fails) = eUtils.cron_query(term,
                  date_from, date_to)
            template_values = {
               'abstr_list': abstr_list
            }
            path = os.path.join(os.path.dirname(__file__), 'hits.html')
            suject = "Today on PubMed"
         except eUtils.PubMedException, error:
            template_values = {
               'pair_list': error.pair_list
            }
            path = os.path.join(os.path.dirname(__file__), 'error.html')
            subject = "Error report: pubcron"
         except eUtils.NoHitException:
            # Don't send mail if no hit.
            continue

         # Create the email message (with hits or error report).
         msg = mail.EmailMessage()
         msg.initialize(to=user_data.user.email(),
            sender="guillaume.filion@gmail.com",
            subject=subject, body="Message in HTML format.",
            html=template.render(path, template_values))
         msg.send()


application = webapp.WSGIApplication([
  ("/send", Sender),
], debug=True)

def main():
   run_wsgi_app(application)

if __name__ == '__main__':
    main()
