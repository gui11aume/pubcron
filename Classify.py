# -*- coding: utf-8 -*-
import re
from math import log

# Here-list of title stop-words.
stopw = ('and', 'the', 'of', 'a', 'in', 'to', 'at', 'by',
         'as', 'with', 'via', 'is', 'are', 'from', 'for',
         'an', 'into', 'non', 'not', 'no')

def to_words(string):
   string = string.lower().replace('-', ' ')
   # Remove punctuation.
   for sign in (':', '?', '.', ',', ';'):
      string = string.replace(sign, '')
   # Remove isolated numbers (after replacing dash by space).
   string  = re.sub(' [0-9]+ ', ' ', string)
   # Split, remove stopwords.
   return [w for w in string.split(' ') if not w in stopw]

def update_score(abstr_list, rlvt, irlvt, pos, neg):
   pos = pos.split(':')
   neg = neg.split(':')
   # Initial log-ratio (relevant fraction).
   init_logratio = log(1 + rlvt) - log(2 + rlvt + irlvt)
   # Constant Bayesian log-ratio.
   clogratio = log(len(neg_terms) + len(set(neg_terms))) - \
         log(len(pos) + len(set(neg)))
   for abstr in abstr_list:
      words = to_words(abstr.title)
      # Compute the Bayesian score.
      score = init_logratio
      for w in words:
         score += clogratio + log(1 + pos.count(w)) - \
               log(1 + neg.count(w))
      # Set 'words' and 'score' attributes.
      abstr.words = ':'.join(words)
      abstr.score = round(score, 2)
