import os
import datetime

import eUtils

from pubcron import UserData, term_key
from Classify import update_score

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


def mail_admin(user, error):
   mail.send_mail("pubcron.mailer@gmail.com",
                  "pubcron.mailer@gmail.com",
                  "Pubcron mail report",
                  "User %s:\n%s" % (user, str(error)))

class Despatcher(webapp.RequestHandler):
   """Called by the cron scheduler. Query PubMed with all the
   saved user terms and send them a mail."""

   def get(self):

      # DEBUG
      admin = cron = ''
      if users.is_current_user_admin():
         admin = 'admin'
      if self.request.headers.get("X-AppEngine-Cron"):
         cron = 'cron'

      # Get all user data.
      data = UserData.gql("WHERE ANCESTOR IS :1", term_key())

      for user_data in data:
         term = str(user_data.term)

         # Update last time run.
         last_run = user_data.last_run
         user_data.last_run = datetime.datetime.now()
         user_data.put()

         # Skip user if term is not valid (or empty incidentally).
         if not user_data.term_valid:
            continue

         path = None
         subject = None

         yesterday = datetime.datetime.today() + \
               datetime.timedelta(days=-1)
         date_from = last_run or yesterday
         date_to = max(yesterday, date_from)
         term = "("+term+")" + \
               date_from.strftime("+AND+(%Y%%2F%m%%2F%d:") + \
               date_to.strftime("%Y%%2F%m%%2F%d[crdt])")

         # Fetch the abstracts.
         try:
            raw = eUtils.toAbstr(eUtils.fetch_abstracts(term))
            # Get the parsed abstracts with a body.
            #TODO: Check the fails.
            abstr_list = [a for a in raw if a.body and not a.fail]

            update_score(
                  abstr_list,
                  len(user_data.relevant_ids.split(':')),
                  len(user_data.irrelevant_ids.split(':')),
                  user_data.positive_terms,
                  user_data.negative_terms
               )

            template_values = {
               'user': user_data.user.nickname(),
               'abstr_list': sorted(abstr_list, reverse=True)
            }
            path = os.path.join(os.path.dirname(__file__), 'hits.html')
            subject = "Recently on PubMed"
            #TODO: this lines causes an error. Why?
#            if admin or cron:
#               subject += " -- % %" % (admin, cron)
         except eUtils.PubMedException, error:
            template_values = {
               'pair_list': error.pair_list
            }
            path = os.path.join(os.path.dirname(__file__), 'error.html')
            subject = "Error report: pubcron"
         except eUtils.NoHitException:
            # Skip user mail if no hit.
            continue
         except Exception, e:
            # For other exceptions, send a mail to amdin.
            mail_admin(str(user_data.user.nickname()), e)
            # And skip user mail.
            continue

         # Create the email message (with hits or error report).
         msg = mail.EmailMessage()
         msg.initialize(to=user_data.user.email(),
            sender="pubcron.mailer@gmail.com",
            subject=subject, body="Message in HTML format.",
            html=template.render(path, template_values))
         msg.send()


application = webapp.WSGIApplication([
  ("/send", Despatcher),
], debug=True)

def main():
   run_wsgi_app(application)

if __name__ == '__main__':
    main()
