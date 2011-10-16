# -*- coding: utf-8 -*-

import sys
import urllib
import urllib2

from SAXmed import eFetchResultHandler, eSearchResultHandler
from xml.sax import make_parser


## CONSTANTS ##

# Base link to eUtils.
BASE = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
# Limit on XML abstracts retrieval.
RETMAX = 100


##########################################
######          Exceptions          ######
##########################################

# eSearch/PubMed Exceptions.
class eSearchException(Exception):
   pass

class NoHitException(eSearchException):
   pass

class PubMedException(eSearchException):
   pass


##########################################
######           Functions          ######
##########################################


def fetch_Abstr(term, **kwargs):
   """Query PubMed and return a list of Abstr instances."""

   Abstr_list = []
   parser = make_parser()
   parser.setContentHandler(eFetchResultHandler(Abstr_list))
   parser.parse(fetch_XML(term, **kwargs))
   return Abstr_list


def fetch_XML(term, **kwargs):
   """Query PubMed and return an XML stream."""

   eSearch_query = {}
   parser = make_parser()
   parser.setContentHandler(eSearchResultHandler(eSearch_query))
   parser.parse(robust_eSearch_query(term, **kwargs))

   # Plug-in the results of eSearch in eFetch.
   return eFetch_query(**eSearch_query)


def eFetch_query(querykey, webenv, **kwargs):
   """Basic eFetch query through QueryKey and WebEnv.
   Return an XML stream."""

   return urllib2.urlopen(BASE + "efetch.fcgi?db=pubmed" \
         + "&query_key=" + querykey \
         + "&WebEnv=" + webenv \
         + "&retmode=xml")


def robust_eSearch_query(term, **kwargs):
   """Robust eSearch query is carried out in two steps: the first
   request returns hit count and meta information (PubMed query
   translation, errors, warnings etc.) on which error checking
   is performed. The second request returns results using
   "usehistory=y", producing QueryKey and WebEnv output fields that
   can be used for future requests or passed on to eFetch."""

   # Initial query to check for errors and get hit count.
   initial_query = {}
   parser = make_parser()
   parser.setContentHandler(eSearchResultHandler(initial_query))
   parser.parse(eSearch_query(
         term = term,
         usehistory = False,
         retmax = 0,
         **kwargs
      ))
   # Check for the presence of "ErrorList".
   if initial_query.get('errors'):
      raise PubMedException(initial_query.get('errors'))

   # Check hit count.
   count = int(initial_query.get('count'))
   if count == 0:
      raise NoHitException(term)

   return eSearch_query(
         term = term,
         usehistory = True,
         retmax = min(count, RETMAX)
   )


def eSearch_query(term, usehistory=False, retmax=0, **kwargs):
   """Basic error-prone eSearch query."""

   usehistory = '&usehistory=y' if usehistory else ''
   extrargs = '&' + urllib.urlencode(kwargs) if kwargs else ''
   return urllib2.urlopen(BASE + "esearch.fcgi?db=pubmed" \
        + '&term=' + term \
        + usehistory \
        + '&retmax=' + str(retmax) \
        + extrargs
     )
