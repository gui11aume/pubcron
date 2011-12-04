# -*- coding: utf-8 -*-

import os
import re
try:
   import json
except ImportError:
   import simplejson as json
from hashlib import sha1

import app_admin
import eUtils
import tfidf

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app


class Feedback(webapp.RequestHandler):
   """Handle PubCron mail relevance feedback update.

   To assert that the POST request is issued from the PubCron mail
   (and not from any other POST-compliant origin), a checksum that
   involves the PMIDs of the articles and a user-specific secret
   salt is recomputed and compared to the checksum sent in the
   request.

   Because users do not know their own secret salt, they cannot
   compute the secure checksum themselves from the PMIDs.

   This allows PubCron to check the user's identify without them
   having to be logged-in (which turned out to cause bugs because
   users still need to log in on PubCron even when they are logged
   in on Gmail)."""

   def validate_request(self, user_data):
      """Check that the request is issued from the PubCron Mail."""
      # get PMIDs of abstracts in the mail.
      pmids = ''.join(sorted([
          pmid \
          for pmid in self.request.arguments() \
          if re.match('[0-9]{8}$', pmid)
      ]))
      # Add a pinch of secret salt.
      checksum = sha1(pmids + user_data.salt).hexdigest()

      return checksum == self.request.get('checksum')


   def validate_pmid(self, pmid_list):
      """PMIDs consist of 8 digits. Check that all passed items
      comply to this format."""
      return all([re.match('^[0-9]{8}$', pmid) for pmid in pmid_list])


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
         return

      # Check that POST is issued from PubCron mail.
      checksum = self.validate_request(user_data)
      if not self.request.get('checksum'):
         # Could not check identity (hacked?!!): good-bye.
         return
      
      # Identity check successful. Do the update.
      new_relevant_pmids = []
      new_irrelevant_pmids = []

      # Process key/value pairs.
      for name in self.request.arguments():
         # NB: only PMID update correspond to 'name' equal to
         # "Yes" or "No". The other cases are either no answer
         # or non PMID POST paramters (like uid or checksum).
         if self.request.get(name) == 'Yes':
            new_relevant_pmids += [name]
         elif self.request.get(name) == 'No':
            new_irrelevant_pmids += [name]

      # It is probably unlikely that a malicious request went
      # until here, but because we are about to save user-
      # submitted data, we do a validity (security) check.
      pmids_to_update = new_relevant_pmids + new_irrelevant_pmids
      if not self.validate_pmid(pmids_to_update):
         # Validation failed: good-bye.
         return

      # From here, PMIDs have been parsed and checked.
      # Now recall and parse user JSON data.
      mu_corpus = json.loads(user_data.mu_corpus or '[]')
      relevant_docs = json.loads(user_data.relevant_docs or '[]')
      irrelevant_docs = json.loads(user_data.irrelevant_docs or '[]')

      # Clear new docs from user data (in case users are notifying
      # that they change their mind on relevance).
      pmids_to_update = new_relevant_pmids + new_irrelevant_pmids
      for relevant_then_irrelevant in (relevant_docs, irrelevant_docs):
         for doc in relevant_then_irrelevant:
            if doc.get('pmid') in pmids_to_update:
               relevant_then_irrelevant.remove(doc)


      # Now, get the PubMed data and compute tf-idf.
      for (new_ids, doc_list) in (
            (new_relevant_pmids, relevant_docs),
            (new_irrelevant_pmids, irrelevant_docs)):

         new_docs = eUtils.fetch_ids(new_ids)
         new_tfidf = tfidf.compute_from_texts(
             [abstr.get('text', '') for abstr in new_docs],
             mu_corpus.values()
         )
         for (doc, tfidf_dict) in zip (new_docs, new_tfidf):
            # Keep only fields 'pmid' and 'title'.
            for field_name in doc.keys():
               if not field_name in ('pmid', 'title'):
                  doc.pop(field_name, None)
            # Add field 'tfidf'.
            doc['tfidf'] = tfidf_dict
         # Append to user data.
         doc_list.extend(new_docs)


      # Update the documents...
      user_data.relevant_docs = db.Text(
           json.dumps(relevant_docs)
      )
      user_data.irrelevant_docs = db.Text(
           json.dumps(irrelevant_docs)
      )
      # ... and put.
      user_data.put()

      # Now reassure the user with a warm HTML page :-)
      dot = os.path.dirname(__file__)
      template_path = os.path.join(dot, 'pubcron_template.html')
      content_path = os.path.join(dot, 'content',
            'feedback_content.html')

      template_values = {
         'page_title': 'PubCron feedback',
         'page_content': open(content_path).read(),
      }
      self.response.out.write(
         template.render(template_path, template_values)
      )


application = webapp.WSGIApplication([
  ('/feedback', Feedback),
], debug=True)


def main():
   run_wsgi_app(application)


if __name__ == '__main__':
    main()
