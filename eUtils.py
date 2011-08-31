# -*- coding: utf-8 -*-

import sys
import urllib
import urllib2
import datetime as dt

from xml.dom import minidom

## CONSTANTS ##
BASE = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
RETMAX = 5000

# Convenience XML extraction functions.
def unlist_or_raise(nodelist, tag):
   if len(nodelist) > 1:
      raise MultipleTagsException(tag)
   return nodelist[0]

def _nodes(node, tag):
   return node.getElementsByTagName(tag)

def _node(node, tag):
   return unlist_or_raise(_nodes(node, tag), tag)

def _data(node, tag):
   extract = unlist_or_raise(_nodes(node, tag), tag)
   return extract.firstChild.data if extract else None

def _child_of(node, tag):
   for child in _nodes(node, tag):
      if child.parentNode is node: return child



##########################################
######          Exceptions          ######
##########################################

# eSearch Exceptions.
class eSearchException(Exception):
   pass

class RetMaxExceeded(eSearchException):
   pass

class NoHitException(eSearchException):
   pass

class PubMedError(eSearchException):
   def __init__(self, xmldoc):
      self.xmldoc = xmldoc

   def __str__(self):
      return self.xmldoc.toxml()

# XML Exceptions.
class XMLException(Exception):
   pass

class MultipleTagsException(XMLException)
   pass


##########################################
######           XMLabstr           ######
##########################################

class XMLabstr:
   """Representation of a PubMed Abstract parsed by minidom.
   Only implements a constructor that specifies static attributes
   for easier use in Django templates."""

   def __init__(self, abstr):
      self.abstr = abstr

      # PubMed ID.
      self.pmid = _child_of(_node(abstr, "MedlineCitation"), \
            "PMID").firstChild.data

      # Article Language.
      self.language = _data(abstr, "Language")

      # Journal and publication types.
      self.journal = _data(_node(abstr, "Journal"), "Title")
      self.pubtypes = [node.firstChild.data for node in \
           _nodes(abstr, "PublicationType")]

      # Authors.
      self.authors = ", ".join([_data(auth, "ForeName") + " " + \
            _data(auth, "LastName") for auth in _nodes(abstr, "Author")])
      self.initials = ", ".join([_data(auth, "Initials") + " " + \
            _data(auth, "LastName") for auth in _nodes(abstr, "Author")])

      # MeSH terms.
      self.majorMeSH = [node.firstChild.data for node in \
            _nodes(abstr, "DescriptorName") if \
            node.attributes["MajorTopicYN"].value == "Y"]
      self.minorMeSH = [node.firstChild.data for node in \
            _nodes(abstr, "DescriptorName") if \
            node.attributes["MajorTopicYN"].value == "N"]

      # Publication date as a string.
      self.pubdate = " ".join([_data(_node(abstr, "PubDate"), ymd) or "" \
            for ymd in ("Month", "Day", "Year")])

      # Article Title and abstract text.
      self.title = _data(abstr, "ArticleTitle")
      self.body = _data(abstr, "AbstractText")



##########################################
######           Functions          ######
##########################################

def cron_query(term, date_from=None, date_to=None):
   """Cron wrapper allowing to perform a request with the same term
   at different dates. Return a list of XMLabstr objects."""
   date_from = date_from if date_from else \
         dt.datetime.today() + dt.timedelta(-1)
   date_to = date_to if date_to else date_from
   #term += date_from.strftime("%Y/%m/%d:") + \
   term = "filion+gj[author]"
   ablist = []
   for xml in _nodes(minidom.parseString(fetch_abstracts(term)), \
         "PubmedArticle"):
         ablist.append(XMLabstr(xml))
   return ablist


def fetch_abstracts(term):
   """Query PubMed and return PubmedArticleSet in (non parsed)
   XMLformat, or None if no hit."""
   try:
      xmldoc = robust_eSearch_query(term)
   except NoHitException:
      return None
   return eFetch_query(
         key = _child_of(_node(xmldoc, "eSearchResult"), \
               "QueryKey").firstChild.data,
         webenv = _child_of(_node(xmldoc, "eSearchResult"), \
               "WebEnv").firstChild.data)


def eFetch_query(key, webenv):
   """Basic eFetch query through QueryKey and WebEnv."""
   return urllib2.urlopen(BASE + "efetch.fcgi?db=pubmed" \
         + "&query_key=" + key \
         + "&WebEnv=" + webenv \
         + "&retmode=xml").read()


def robust_eSearch_query(term):
   """Robust eSearch query is carried out in two steps: the first
   request returns hit count and meta information (PubMed query
   translation, errors, warnings etc.) on which error checking
   is performed. The second request returns results using
   "usehistory=y", producing QueryKey and WebEnv output fields that
   can be used for future requests or passed on to eFetch."""
   # Initial query to check for errors and get hit count.
   xmldoc = minidom.parseString(eSearch_query(term=term,
         usehistory=False, retmax=0))
   # Check for PubMedErrors. Return the xml result for diagnostic in
   # case of ErrorList tag.
   if _nodes(xmldoc, "ErrorList"):
      raise PubMedError(xmldoc)

   # Get and control hit count.
   count = int(_child_of(_node(xmldoc, "eSearchResult"), \
         "Count").firstChild.data)
   if count > RETMAX:
      raise RetMaxExceeded(count)
   if count == 0:
      raise NoHitException

   return minidom.parseString(eSearch_query(term=term,
         usehistory=True, retmax=count))


def eSearch_query(term, usehistory=False, retmax=0):
   """Basic error-prone eSearch query."""
   usehistory = "&usehistory=y" if usehistory else ""
   return urllib2.urlopen(BASE + "esearch.fcgi?db=pubmed" \
        + "&term=" + term \
        + usehistory \
        + "&retmax=" + str(retmax)).read()
