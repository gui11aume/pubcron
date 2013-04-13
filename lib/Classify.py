# -*- coding: utf-8 -*-

import tfidf

def update_score_inplace(abstr_list, relevant_docs,
      irrelevant_docs, mu_corpus=[]):

   """Update in place the 'score' field of JSON-like documents.

   The relevance score of a given abstract a is (math notation):
   max {cosine(a,r) | r relevant} - max {cosine(a,i) | i rrelevant}"""

   new_texts = [abstr['text'] for abstr in abstr_list]
   new_tfidfs = tfidf.compute_from_texts(new_texts, mu_corpus)

   for (doc, new_tfidf) in zip(abstr_list, new_tfidfs):
      cosine_relevant = [
            tfidf.cosine(new_tfidf, relevant_doc['tfidf']) \
            for relevant_doc in relevant_docs
      ]
      cosine_irrelevant = [
            tfidf.cosine(new_tfidf, irrelevant_doc['tfidf']) \
            for irrelevant_doc in irrelevant_docs
      ]
      doc['score'] = 10 * round(
             max(cosine_relevant) - max(cosine_irrelevant), 3
      )
