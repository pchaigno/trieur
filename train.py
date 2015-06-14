#!/usr/bin/env python
from sklearn.datasets import load_files
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.grid_search import GridSearchCV
from sklearn import cross_validation
import numpy

# Loads emails.
emails = load_files(container_path='emails', shuffle=True, random_state=42)

# Trains classifier:
pipeline = Pipeline([('vect', CountVectorizer(decode_error='ignore')),
					('tfidf', TfidfTransformer()),
					('clf', MultinomialNB())
					#('clf', SGDClassifier(loss='hinge', penalty='l2', alpha=1e-3, n_iter=5, random_state=42))
					])
parameters = {'vect__ngram_range': [(1, 1), (1, 2)],
				'tfidf__use_idf': (True, False),
				'clf__alpha': (1e-2, 1e-3)
			}
grid_search = GridSearchCV(pipeline, parameters, n_jobs=4)
clf = grid_search.fit(emails.data, emails.target)

# Performs tenfold cross-validation: 
scores = cross_validation.cross_val_score(clf, emails.data, emails.target, cv=10)
print(scores)
print("Accuracy: %0.2f (+/- %0.2f)" % (scores.mean(), scores.std() * 2))
