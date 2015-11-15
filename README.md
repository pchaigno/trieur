# Trieur

Ultimately, this project will automatically classify your mails into the right folders.
Right now, I need help to validate my first simple implementation.


## Usage & Validation

0. Retrieve the project: `git clone https://github.com/pchaigno/trieur && cd trieur/`.
0. Install the dependencies: `sudo apt-get install gfortran libopenblas-dev liblapack-dev && sudo pip install -r requirements.txt`
0. Download your emails: `./imap.py imap_server path/to/temp/folder`.
0. Test the Bayesian classifier: `./train.py path/to/temp/folder`.
0. Test the SVM classifier: `./train.py -c SGDClassifier path/to/temp/folder`.
0. If the accuracy computed through the tenfold cross-validation is below 90% please open an issue with your results and the name of your mailbox folders.


## How does it work?

`imap.py` downloads emails from your mailbox folders. `train.py` then creates a classifier with the given algorithm (e.g. Bayesian) and tunes it (computes the best parameters by cross-validation). Finally, it displays the result of the tenfolds cross-validation.


## Frequently Asked Questions

Please see the [Frequently Asked Questions page](https://github.com/pchaigno/trieur/wiki/Frequently-Asked-Questions) for answers to your questions. Don't hesitate to open an issue if your question is not answered in the Wiki.


## License

This project is under [MIT license](LICENSE).
