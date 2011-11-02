# -*- coding: utf-8 -*-

# The following code is largely inspired, or I should say pirated
# from the nltk module, (which I do not import because I use only
# a tiny fraction of it.

import re
from math import log
from porter import PorterStemmer

class Corpus():
   """Collection of texts, stemmed by by the Porter stemmer.
   Provides tf-idf calculation."""

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
      # Tokenize the texts.
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
      self.texts = [ \
            [w for w in txt if not w in self.stopw] \
            for txt in texts
      ]

   def tf(self, term, index = 0):
      txt = self.texts[index]
      return float(txt.count(self.stem(term))) / len(txt)

   def idf(self, term):
      nmatch = sum([1 for txt in self.texts if self.stem(term) in txt])
      # Will fail with ZeroDivisionError if no match.
      return log(len(self.texts) / float(nmatch))

   def tfidf(self, term, index = 0):
      try:
         return self.tf(term, index) * self.idf(term)
      except ZeroDivisionError:
         # 'term' is not present in the corpus.
         return 0.0
