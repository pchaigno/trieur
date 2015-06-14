#!/usr/bin/env python
from sklearn.datasets import load_files
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.grid_search import GridSearchCV
from sklearn import cross_validation
import numpy


"""Trains a classifier from sample files.

Args:
	classifier_type: Type of the classifier (either MultinomialNB or SGDClassifier).

Returns:
	Trained classifier tuned using grid search.
"""
def train_classifier(emails, classifier_type = 'MultinomialNB'):
	# Instantiates classifier:
	if classifier_type == "SGDClassifier":
		classifier = SGDClassifier(loss='hinge', penalty='l2', alpha=1e-3, n_iter=5, random_state=42)
	else:
		classifier = MultinomialNB()

	# Trains and tunes classifier:
	pipeline = Pipeline([('vect', CountVectorizer(decode_error='ignore')),
						('tfidf', TfidfTransformer()),
						('clf', classifier)
						])
	parameters = {'vect__ngram_range': [(1, 1), (1, 2)],
					'tfidf__use_idf': (True, False),
					'clf__alpha': (1e-2, 1e-3)
				}
	grid_search = GridSearchCV(pipeline, parameters, n_jobs=4)
	clf = grid_search.fit(emails.data, emails.target)

	return clf


"""Trains a classifier and performs tenfold cross-validation on it.

"""
if __name__ == "__main__":
	# Loads emails.
	emails = load_files(container_path='emails', shuffle=True, random_state=42)

	classifier = train_classifier(emails, 'MultinomialNB')

	# Performs tenfold cross-validation: 
	scores = cross_validation.cross_val_score(classifier, emails.data, emails.target, cv=10)
	print(scores)
	print("Accuracy: %0.2f (+/- %0.2f)" % (scores.mean(), scores.std() * 2))
