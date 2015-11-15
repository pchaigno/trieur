#!/usr/bin/env python
import imaplib
import re
import pprint
import sys
import os
import getpass
import argparse
import email
import chardet
from bs4 import BeautifulSoup

# Regular expression to parse folder names from imaplib.
list_response_pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')

# List of common folder names to ignore.
ignore = ['Sent', 'Trash', 'INBOX', 'Brouillons', 'Corbeille', 'Draft', 'Junk']


"""Extract text parts of a HTML document.

Uses BeautifulSoup for that purpose.

Args:
	html: HTML document encoded in UTF-8.

Returns:
	Text parts of the HTML document.
"""
def html2text(html):
	soup = BeautifulSoup(html, "lxml")
	for script in soup(["script", "style"]):
	    script.extract()
	text = soup.get_text().encode('utf8')
	lines = (line.strip() for line in text.splitlines())
	chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
	text = '\n'.join(chunk for chunk in chunks if chunk)
	return text


"""Reads the list of leaf folders from the mailbox.

A leaf folder is a folder without any child folder.

Args:
	connection: Opened connection to the mailbox.

Returns:
	List of leaf folders.
"""
def get_folders(connection):
	typ, data = connection.list()

	folders = []
	for line in data:
		flags, delimiter, folder = list_response_pattern.match(line).groups()
		folder = folder.strip('"')
		if flags == '\\HasNoChildren':
			folders.append(folder)
	return folders


"""Reencode a text in UTF-8.

A given charset can be tried first.
If decoding with that charset fails, falls back to the default behaviour.
Tries to detect the encoding using chardet library.

Args:
	text: Text with different encoding, possibly unknown.
	charset: Possible encoding for the text.

Returns:
	Same text encoded in UTF-8.
"""
def reencode(text, charset = None):
	if charset == "us-ascii":
		text = text.decode('utf8')
	elif charset:
		try:
			text = text.decode(charset)
		except (LookupError, UnicodeDecodeError):
			result = chardet.detect(text)
			text = text.decode(result['encoding'])
	else:
		result = chardet.detect(text)
		if result['encoding']:
			text = text.decode(result['encoding'])
	return text.encode('utf8')


"""Decodes a payload from an email body and reencodes it in UTF-8.

If the email body is a HTML document, will extract text from that document.

Args:
	payload: Email body payload.

Returns:
	Tuple with a boolean to True if the payload was a HTML document
	and email payload as text encoded in UTF-8.
"""
def get_decoded_email_payload(payload):
	content_type = payload.get_content_type()
	if content_type != "text/plain" and content_type != "text/html":
		return None

	charset = payload.get_content_charset()
	text = payload.get_payload(decode=True)
	text = reencode(text, charset)

	if text is None:
		return None

	if payload.get_content_type() == 'text/plain':
		return (False, text.strip())

	# If it's a HTML document we need to extract the text
	# and reencode it to be sure:
	text_encoded = html2text(text.strip())
	text = reencode(text_encoded)
	return (True, text)


"""Decodes an email body and reencodes it in UTF-8.

If the email body is a HTML document, will extract text from that document.

Args:
	msg: Raw message body with different encoding, possibly un-specified.

Returns:
	Message body as text encoded in UTF-8.
"""
def get_decoded_email_body(msg):
	if msg.is_multipart():
		html_text = None
		# Iterates on message parts to find one we can use:
		for payload in msg.get_payload():
			content_type = payload.get_content_type()
			if content_type !=  None:
				continue

 			# Extracts what we can from the payload:
 			text_object = get_decoded_email_payload(payload)
			if text is not None:
				(is_html, text) = text_object
				if is_html:
					return text_object
				else:
					html_text = text

		# Only uses the HTML part if no text part was found.
		if html_text is not None:
			return (True, html_text)
		else:
			return None

	else:
		return get_decoded_email_payload(msg)


"""Retrieves all messages from a given folder.

Args:
	connection: Opened connection to the mailbox.
	folder: Folder to retrieve.

Returns:
	List of 5-tuples representing emails.
	5-tuples have the format (subject, to, from, is_html?, body)
"""
def retrieve_messages(connection, folder):
	connection.select(folder, readonly=True)

	# Iterates on messages in the folder:
	messages = []
	i = 1
	while True:
		try:
			mail = connection.fetch(i, '(RFC822)')[1][0]
		except imaplib.IMAP4_SSL.error:
		# Usually means we reached the last folder.
			break

		# Some implementations return None instead of throwing an error:
		if not mail:
			break
		(typ, msg_data) = mail
		if not msg_data or not msg_data[0]:
			break

		# Reads and adds message to the list:
		msg = email.message_from_string(msg_data)
		text, encoding = email.Header.decode_header(msg['subject'])[0]
		subject = reencode(text, encoding)
		body_object = get_decoded_email_body(msg)
		if body_object:
			(is_html, text_body) = body_object
			if text_body:
				messages.append((subject, msg['to'], msg['from'], is_html, text_body))

		i += 1

	return messages


"""Opens a connection to an IMAP server.

Args:
	imap_server: Address of the IMAP server.
	username: Username to login on the IMAP server.
	password: Password associated to that username.

Returns:
	Opened connection to the mailbox
"""
def connect(imap_server, username, password):
	connection = imaplib.IMAP4_SSL(imap_server)
	connection.login(username, password)
	return connection


"""Reads emails from leaf folders of a email account and writes them on the disk.

Connection is opened in SSL.
"""
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Reads emails from leaf folders of an email account and writes them on the disk.')
	parser.add_argument('imap_server', type=str,
		help='Address of the IMAP server.')
	parser.add_argument('output_dir', type=str,
		help='Directory where the emails will be writen, in folders matching the mailbox folders.')
	parser.add_argument('-m', '--min-nb-emails', type=int, default=10,
		help='Minimum number of emails in a folder to be retrieved. Default is 10. Folders with too few emails are useless for the classifier.')
	args = parser.parse_args()

	username = raw_input("Username: ")
	password = getpass.getpass()
	connection = connect(args.imap_server, username, password)

	# Retrieves folder list.
	folders = get_folders(connection)

	num_mail = 0
	for folder in folders:
		if not folder in ignore:
			print("%s:" % folder.upper())

			# Retrieves all messages in the folder.
			messages = retrieve_messages(connection, folder)

			if len(messages) >= args.min_nb_emails:
				# Creates directory if it doesn't exist:
				directory = os.path.join(args.output_dir, folder.replace('/', '__').replace(' ', '_'))
				if not os.path.exists(directory):
					os.makedirs(directory)

				for message in messages:
					subject = message[0]
					recipient = message[1]
					sender = message[2]
					mail_content = message[4]
					print(subject)

					# Writes message to file:
					fo = open(os.path.join(directory, str(num_mail)), "wb")
					fo.write(subject)
					if recipient:
						fo.write(recipient)
					if sender:
						fo.write(sender)
					fo.write(mail_content)
					fo.close()

					num_mail += 1
			else:
				# Only saves messages if there are enough in the folder.
				print("Not enough mails to train.")

			print("")
			print("")
