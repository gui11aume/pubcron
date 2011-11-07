# -*- coding: utf-8 -*-

import tfidf

def update_score_inplace(test, relevant, irrelevant, aux=[]):
   """Update in place the 'score' attribute of Abstr instances
   in the 'test' iterable. The relevance score is the difference
   between the max cosine similarities with relevant and irrelevant
   documents of the corpus."""

   n1 = len(test)
   n2 = len(test) + len(relevant)
   n3 = len(test) + len(relevant) + len(irrelevant)

   main_corpus = [a.text for a in test + relevant + irrelevant]
   aux_corpus = [a.text for a in aux]

   I = tfidf.CorpusIndex(main_corpus, aux_corpus)
   for i in range(n1):
      test[i].score = 10 * round(
             max([I.cosine(i,j) for j in range(n1, n2)]) - \
             max([I.cosine(i,j) for j in range(n2, n3)]), 3
         )



