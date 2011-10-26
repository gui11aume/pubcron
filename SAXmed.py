# -*- coding: utf-8 -*-

from xml.sax import handler
from xml.sax.saxutils import escape

class eSearchResultHandler(handler.ContentHandler):
   """Parse PubMed eSearch XML results."""

   ROOT = ('eSearchResult',)
   # Fields of interest.
   FIELDS = {
      ROOT + ('Count',): 'count',
      ROOT + ('QueryKey',): 'query_key',
      ROOT + ('WebEnv',): 'WebEnv'
   }

   def __init__(self, termdict):
      self._stack = []
      self._errors = False
      self.data = ''
      # 'termdict' passed by reference.
      self.termdict = termdict

   def startElement(self, name, attrs):
      self.data = ''
      self._stack.append(name)
      if name == 'ErrorList':
         self._errors = True
         self.termdict['errors'] = []

   def endElement(self, name):
      if name == 'ErrorList': self._errors = False

      field = self.FIELDS.get(tuple(self._stack))
      # Update the given field by list-append.
      if field:
         self.termdict[field] = self.data
      if self._errors:
         # Within the "ErrorList" node.
         self.termdict['errors'].append(
               (self._stack[-1:], self.data.strip())
         )

      self._stack.pop()
      self.data = ''

   def characters(self, data):
      self.data += data


class eFetchResultHandler(handler.ContentHandler):
   """Parse PubMed eFetch XML results."""

   class Abstr:
      """Only a namespace for this module. But Abstr isntances
      can be sorted based on scores, if given as attributes."""

      def __lt__(self, other):
         return self.score < other.score

      def __getattr__(self, attr):
         if attr == 'text':
            self.text = ''
            return ''
         else:
            raise AttributeError

   ROOT = ('PubmedArticleSet', 'PubmedArticle', 'MedlineCitation')
   ARTICLE = ROOT + ('Article',)
   JOURNAL = ARTICLE + ('Journal',)
   # Fields of interest.
   FIELDS = {
      ROOT + ('PMID',): 'pmid',
#     JOURNAL + ('JournalIssue', 'Volume'): 'vol',
#     JOURNAL + ('JournalIssue', 'Issue'): 'issue',
      JOURNAL + ('JournalIssue', 'PubDate', 'Year'): 'year',
      JOURNAL + ('JournalIssue', 'PubDate', 'Month'): 'month',
      JOURNAL + ('JournalIssue', 'PubDate', 'Day'): 'day',
      JOURNAL + ('Title',): 'jrnl',
      ARTICLE + ('ArticleTitle',): 'title',
#     ARTICLE + ('Pagination', 'MedlinePgn'): 'page',
      ARTICLE + ('Abstract', 'AbstractText'): 'text',
      ARTICLE + ('AuthorList', 'Author', 'LastName'): 'name',
#     ARTICLE + ('AuthorList', 'Author', 'ForeName'): 'forename',
      ARTICLE + ('AuthorList', 'Author', 'Initials'): 'intls',
#     ARTICLE + ('Language',): 'language',
#     ARTICLE + ('PublicationTypeList', 'PublicationTypes'): 'pubtypes',
#     ROOT + ('MeshHeadingList', 'MeshHeading', 'DescriptorName'): 'mesh'
   }

   def __init__(self, abstr_list):
      handler.ContentHandler.__init__(self)
      self._dict = {}
      self._stack = []
      self.data = ''
      # 'abstr_list' passed by reference.
      self.abstr_list = abstr_list

   def startElement(self, name, attrs):
      self.data = ''
      self._stack.append(name)
      if name == 'PubmedArticle': self.clear()

   def endElement(self, name):

      if name == 'PubmedArticle': self.wrap()

      field = self.FIELDS.get(tuple(self._stack))
      # Update the given field by list-append.
      if field:
         self._dict[field] = self._dict.get(field, []) + \
               [escape(self.data.strip())]

      self._stack.pop()
      self.data = ''

   def characters(self, data):
      self.data += data

   def clear(self):
      """Erase the dictionary."""
      self._dict.clear()

   def wrap(self):
      """Wrap an instance  of Abstr with few attributes."""
      # Define attributes 'journal', 'pubdate', 'title', 'authors'
      # 'pmid' and 'text'.
      try:
         abstr = self.Abstr()
         abstr.journal = ''.join(self._dict['jrnl'])
         abstr.pubdate = ' '.join(
               self._dict.get('month', []) + \
               self._dict.get('day', [])   + \
               self._dict.get('year', [])
         )
         abstr.title = ''.join(self._dict['title'])
         abstr.authors = ', '.join([' '.join(a) \
               for a in zip(self._dict['intls'], self._dict['name'])])
         abstr.pmid = self._dict['pmid'][0]
         abstr.text = ''.join(self._dict['text'])
      # If an abstract misses any of those attributes, skip it.
      except KeyError:
         pass

      self.abstr_list.append(abstr)
