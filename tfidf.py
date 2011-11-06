# -*- coding: utf-8 -*-

# The following code is inspired from the nltk module (which
# I do not import because I use only a tiny fraction of it).

import re
from math import log, sqrt
from porter import PorterStemmer
from collections import defaultdict

class CorpusIndex():
   """Collection of term/tfidf dictionaries, where terms
   are lower-cased and stemmed by by the Porter stemmer."""

   ## -----------------------    DATA    ------------------------ ##
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


   def __init__(self, texts, aux=[]):
      """Initialize with an iterable of texts. The parameter
      'aux' is a part of the corpus that is used only for
      computing idf."""

      # Get a free Porter stemmer for EVERY initialization!
      self.stem = PorterStemmer().stem
      texts = [self.preprocess(txt, self.stem) for txt in texts]
      aux = [self.preprocess(ax, self.stem) for ax in aux]

      # Compute term and document frequencies.
      docf = defaultdict(int)
      termf_dicts = []
      for txt in texts:
         # Count words in text.
         wcounts = defaultdict(int)
         total = 0.0
         for word in txt:
            wcounts[word] += 1
            total += 1.0
         # Compute term frequencies, update doc frequencies.
         tf = {}
         for word in wcounts:
            tf[word] = wcounts[word] / total
            docf[word] += 1
         # Store term frequencies in 'termf_dicts'.
         termf_dicts.append(tf)

      # Add the terms in auxiliary corpus to doc frequencies.
      for txt in aux:
         for w in set(txt): docf[word] += 1

      # Last loop to compute tf-idf scores.
      corpus_size = len(texts) + len(aux)
      self.tfidf = []
      for tf in termf_dicts:
         thistfidf = {}
         for w in tf:
            thistfidf[w] = tf[w] * log(corpus_size / float(docf[w]))
         self.tfidf.append(thistfidf)

   def preprocess(self, txt, stem):
      # NB: The memory usage is about 2 Mb per 100 PubMed abstracts.
      # Lower-case and tokenize the texts, also remove numbers.
      txt = re.sub(
         # 2. Remove numbers.
            ' [0-9]+ ',
            ' ',
         re.sub(
         # 1. Replace split chars.
            '[-)(!?}{:;,\.\[\]]',
            ' ',
            txt
         # 3. Split on spaces.
         )).lower().split()
      # Stem the tokens and remove stop words.
      return (w for w in (stem(w) for w in txt) if not w in self.stopw)


   def cosine(self, index_a, index_b):
      """Compute the cosine similarity between two documents."""
      tfidf_a = self.tfidf[index_a]
      tfidf_b = self.tfidf[index_b]
      numerator = sum([
            tfidf_a[w] * tfidf_b[w] \
            for w in set(tfidf_a).intersection(tfidf_b)
         ])
      denominator = sqrt(
            sum([v**2 for v in tfidf_a.values()]) * \
            sum([v**2 for v in tfidf_b.values()])
         )

      return numerator / denominator
