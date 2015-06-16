# Trieur

Ultimately, this project will automatically classify your mails into the right folders.
Right now, I need help to validate my first simple implementation.


Usage & Validation
====

0. Retrieve the project: `git clone https://github.com/pchaigno/trieur && cd trieur/`.
0. Download your emails: `./imap.py imap_server path/to/temp/folder`.
0. Test the Bayesian classifier: `./train.py path/to/temp/folder`.
0. Test the SVM classifier: `./train.py -c SGDClassifier path/to/temp/folder`.
0. If the accuracy computed through the tenfold cross-validation is below 90% please open an issue with your results and the name of your mailbox folders.
