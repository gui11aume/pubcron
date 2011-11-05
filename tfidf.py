# -*- coding: utf-8 -*-

# The following code is inspired from the nltk module (which
# I do not import because I use only a tiny fraction of it).

import re
from math import log
from porter import PorterStemmer
from collections import defaultdict

class Index():
   """Collection of term/occurrence dictionaries, where terms
   are lower-cased and stemmed by by the Porter stemmer.Also
   Provides fast tf-idf calculation."""

   ## ----------------------    DATA    ---------------------- ##
   stopw = set(('a', 'about', 'again', 'all', 'almost', 'also',
      'although', 'alway', 'among', 'an', 'and', 'anoth', 'ani',
      'are', 'as', 'at', 'be', 'becaus', 'been', 'befor', 'between',
      'both', 'but', 'by', 'can', 'could', 'did', 'do', 'doe',
      'done', 'due', 'dure', 'each', 'either', 'enough', 'especi',
      'etc', 'for', 'found', 'from', 'further', 'had', 'ha', 'have',
      'here', 'how', 'howev', 'i', 'if', 'in', 'into', 'is', 'it',
      'itself', 'just', 'kg', 'km', 'made', 'mainli', 'make', 'may',
      'mg', 'might', 'ml', 'mm', 'most', 'mostli', 'must', 'nearli',
      'neither', 'no', 'non', 'nor', 'not', 'of', 'often', 'on',
      'our', 'overal', 'perhap', 'pmid', 'quit', 'rather', 'realli',
      'regard', 'seem', 'seen', 'sever', 'should', 'show', 'shown',
      'significantli', 'sinc', 'so', 'some', 'such', 'than', 'that',
      'the', 'their', 'them', 'then', 'there', 'therefor', 'these',
      'they', 'thi', 'those', 'through', 'thu', 'to', 'upon', 'use',
      'variou', 'veri', 'via', 'wa', 'we', 'were', 'what', 'when',
      'which', 'while', 'with', 'within', 'without', 'would'))


   def __init__(self, texts):
      """Initialize with an iterable of texts."""
      # NB: The memory usage is about 2 Mb per 100 PubMed abstracts.
      # Lower-case and tokenize the texts.
      texts = [
            re.sub('[-)(!?}{:;,\.\[\]]', ' ', txt).lower().split() \
            for txt in texts
      ]
      # Stem the tokens (and get a stemmer attribute en passant).
      self.stem = PorterStemmer().stem
      texts = [ \
            [self.stem(w) for w in txt] \
            for txt in texts \
      ]
      # Remove the stop-words.
      texts = [ \
            [w for w in txt if not w in self.stopw] \
            for txt in texts
      ]
      # Build the list of 'defaultdicts'.
      self.dicts = []
      for txt in texts:
         cnt = defaultdict(int)
         for word in txt:
            cnt[word] +=1
            cnt['TOTAL'] += 1
         self.dicts.append(cnt)


   def tf(self, term, index):
      """Return the term frequency in the document of given
      index. Note that stopwords are excluded from the score."""

      return float(self.dicts[index].get(term, 0)) \
            / self.dicts[index]['TOTAL']


   def idf(self, term):
      """Return the inverse document frequency of the term."""

      nmatch = sum([1 for dct in self.dicts if term in dct])
      # Will fail with ZeroDivisionError if no match.
      return log(len(self.dicts) / float(nmatch))


   def tfidf(self, term, index, stemnew=True):
      """Return the tf-idf score of the term in the document
      of given index."""

      # Set stemnew to False if term is taken from the 'Index'.
      if stemnew: term = self.stem(term.lower())

      try:
         return self.tf(term, index) * self.idf(term)
      except ZeroDivisionError:
         # 'term' is not present in the corpus.
         return 0.0
