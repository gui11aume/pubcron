# -*- coding: utf-8 -*-

import sys
import urllib
import urllib2

from xml.dom import minidom


## CONSTANTS ##
BASE = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
RETMAX = 5000 # Limit on XML abstracts retrieval.


# Convenience XML extraction functions.
def _unlist_or_raise(nodelist, tag):
   """Return the first element of a list if length is
   1, empty string if list is empty, or fail withs
   MultipleTagsException if length is greater thana 1."""
   if len(nodelist) > 1:
      raise MultipleTagsException(tag)
   try:
      return nodelist[0]
   except IndexError:
      return u''

def _nodes(node, tag):
   """Return a list of XML nodes with given tag."""
   return node.getElementsByTagName(tag)

def _node(node, tag):
   """Return the content of an XML node with given
   tag if unique, otherwise fail with MultipleTagsException."""
   return _unlist_or_raise(_nodes(node, tag), tag)

def _data(node, tag):
   """Return the data content of a node with given
   tag if unique, otherwise fail with MultipleTagsException."""
   extract = _unlist_or_raise(_nodes(node, tag), tag)
   try:
      return extract.firstChild.data if extract else u''
   except AttributeError:
      # The node exists, but it is empty.
      return u''

def _child_of(node, tag):
   """Return the first direct XML child node of given node
   with given tag."""
   for child in _nodes(node, tag):
      if child.parentNode is node: return child



##########################################
######          Exceptions          ######
##########################################

# eSearch/PubMed Exceptions.
class eSearchException(Exception):
   pass

class RetMaxExceeded(eSearchException):
   pass

class NoHitException(eSearchException):
   pass

class PubMedException(eSearchException):
   pass

# XML Exceptions.
class XMLException(Exception):
   pass

class MultipleTagsException(XMLException):
   pass


##########################################
######             Abstr            ######
##########################################

class Abstr:
   """Representation of a PubMed Abstract parsed by minidom.
   Only implements a constructor that specifies static attributes
   for easier use in Django templates."""

   def __init__(self, abstr):
      self.abstr = abstr

      def brack(string):
         """Convenience method for ref formating."""
         return "(" + string + ")" if string else ""

      # Embed construction in a 'try' statement, then set the 
      # 'fail' attribute.
      try:
         # PubMed ID.
         self.pmid = _child_of(_node(abstr, "MedlineCitation"), \
               "PMID").firstChild.data

         # Article Languages.
         self.languages = _nodes(abstr, "Language")

         # Journal, references and publication types.
         jnode = _node(abstr, "Journal")
         self.journal = _data(jnode, "Title")
         self.ref =  _data(jnode, "Volume") + \
               brack(_data(jnode, "Issue")) + ":" + \
               _data(abstr, "MedlinePgn")

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
         self.pubdate = " ".join([_data(_node(abstr, "PubDate"), mdy) \
               for mdy in ("Month", "Day", "Year")])

         # Article Title and abstract text.
         self.title = _data(abstr, "ArticleTitle")
         self.body = " ".join([x.firstChild.data for x in \
               _nodes(abstr, "AbstractText")])

      except Exception, e:
         # Construction failed, keep the error in attribute 'fail'.
         self.fail = e
      else:
         # Construction succeeded.
         self.fail = False

   def __lt__(self, other):
      """Allow sorting of abstracts. Note that upon construction,
      instances of Abstr have no 'score' attribute so this will
      raise an AttributeError."""
      return self.score < other.score

   def set_score(self, score):
      """Set the 'score' attribute of an instance of Abstr."""
      self.score = score


##########################################
######           Functions          ######
##########################################


def toAbstr(xml):
   """Parse XML string to a list of instances of Abstr."""
   return [Abstr(node) for node in _nodes(minidom.parseString(xml), \
         "PubmedArticle")]

def fetch_abstracts(term, **kwargs):
   """Query PubMed and return PubmedArticleSet in (non parsed)
   XMLformat, or None if no hit."""
   xmldoc = robust_eSearch_query(term, **kwargs)
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


def robust_eSearch_query(term, **kwargs):
   """Robust eSearch query is carried out in two steps: the first
   request returns hit count and meta information (PubMed query
   translation, errors, warnings etc.) on which error checking
   is performed. The second request returns results using
   "usehistory=y", producing QueryKey and WebEnv output fields that
   can be used for future requests or passed on to eFetch."""
   # Initial query to check for errors and get hit count.
   xmldoc = minidom.parseString(eSearch_query(
         term=term,
         usehistory=False,
         retmax=0,
         **kwargs))
   # Check for PubMedExceptions. Return the xml result for diagnostic in
   # case of ErrorList tag.
   if _nodes(xmldoc, "ErrorList"):
      # Send a pairlist as args to PubMedException.
      translation = _data(xmldoc, "QueryTranslation")
      report = [(u"Term (as queried)", term.encode('utf-8')), \
            (u"QueryTranslation", translation)]
      errors = _node(xmldoc, "ErrorList").childNodes
      report += [(nd.nodeName, nd.firstChild.data) for nd in errors]
      raise PubMedException(report)

   # Get and control hit count.
   count = int(_child_of(_node(xmldoc, "eSearchResult"), \
         "Count").firstChild.data)
   if count > RETMAX:
      raise RetMaxExceeded(count)
   if count == 0:
      raise NoHitException(term)

   return minidom.parseString(eSearch_query(term=term,
         usehistory=True, retmax=count))


def eSearch_query(term, usehistory=False, retmax=0, **kwargs):
   """Basic error-prone eSearch query."""
   usehistory = '&usehistory=y' if usehistory else ''
   extrargs = '&' + urllib.urlencode(kwargs) if kwargs else ''
   return urllib2.urlopen(BASE + "esearch.fcgi?db=pubmed" \
        + '&term=' + term \
        + usehistory \
        + '&retmax=' + str(retmax) \
        + extrargs
        ).read()
