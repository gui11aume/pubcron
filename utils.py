# -*- coding:utf-8 -*-

import os
import json
import zlib

import jinja2

import config
import addlibdir
import eUtils
import tfidf


# Globals.
BASE_DIR = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
JINJA_ENV = jinja2.Environment(
          loader=jinja2.FileSystemLoader(TEMPLATE_DIR))

def render(template_name, template_vals={}):
   template = JINJA_ENV.get_template(template_name)
   return template.render(template_vals)


def decrypt(entity, field):
   """Convenience function to extract compressed attributes."""
   return json.loads(zlib.decompress(getattr(entity, field)))


def try_to_update_term(data, term):
   # Spaces cause eUtils queries to fail.
   term = term.replace('\n', '').replace(' ', '+').upper()
   # Minimal check for term inconsistencies.
   for forbidden in ['/', ' ', 'CRDT', 'CRDAT']:
      if forbidden in term: raise TermException(forbidden)
   success = False
   try:
      # If we can create the micro-corpus with the new term,
      # then do the update. Otherwise something went wrong.
      abstr_sample = eUtils.fetch_abstr(
         term = term,
         retmax = config.RETMAX,
         email = config.ADMAIL
      )
      mu_corpus = {}
      for abstr in abstr_sample:
         mu_corpus[abstr['pmid']] = tfidf.preprocess(abstr['text'])
      data.mu_corpus = zlib.compress(json.dumps(mu_corpus))
   except (eUtils.PubMedException, eUtils.NoHitException):
      # PubMed error or no nit.
      success = False
   else:
      success = True

   data.term_valid = success
   data.term = term
   data.put()
   return success
