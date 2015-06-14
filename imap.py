#!/usr/bin/env python
import imaplib
import re
import sys
import os
import email
import chardet
from bs4 import BeautifulSoup

# Regular expression to parse folder names from imaplib.
list_response_pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')

# List of common folder names to ignore.
ignore = ['Trash', 'INBOX', 'Brouillons', 'Corbeille', 'Draft', 'Junk']


"""Extract text parts of a HTML document.

Uses BeautifulSoup for that purpose.

Args:
	html: HTML document encoded in UTF-8.

Returns:
	Text parts of the HTML document.
"""
def html2text(html):
	soup = BeautifulSoup(html)
	for script in soup(["script", "style"]):
	    script.extract()
	text = soup.get_text()
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


"""Decodes an email body and reencode it in UTF-8.

If the email body is a HTML document, will extract text from that document.

Args:
	msg: Raw message body with different encoding, possibly un-specified.

Returns:
	Message body as text encoded in UTF-8.
"""
def get_decoded_email_body(msg):
	text = ""
	if msg.is_multipart():
		html = None
		for part in msg.get_payload():
			if part.get_content_charset() is None:
				continue
 
			charset = part.get_content_charset()
 
			if part.get_content_type() == 'text/plain':
				text = part.get_payload(decode=True)
				text = reencode(text, charset)

			if part.get_content_type() == 'text/html':
				html = part.get_payload(decode=True)
				html = reencode(html, charset)
 
		if text is not None:
			return (False, text.strip())
		elif html is not None:
			text_encoded = html2text(html.strip())
			text = reencode(text_encoded)
			return (True, text)
		else:
			return None
	elif msg.get_content_type() == 'text/plain' or msg.get_content_type() == 'text/html':
		text = reencode(msg.get_payload(decode=True), msg.get_content_charset())
		is_html = msg.get_content_type() == 'text/html'
		return (is_html, text.strip())


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

	messages = []
	i = 1
	while True:
		try:
			mail = connection.fetch(i, '(RFC822)')[1][0]
		except imaplib.IMAP4_SSL.error:
			break
		if not mail:
			break
		(typ, msg_data) = mail
		if not msg_data or not msg_data[0]:
			break
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


"""Reads emails from leaf folders of a mail account and writes them on the disk.

Connection is opened in SSL.

Information to connect to the mail account must be in a 'password' file
with the following format: imap_server_address:login:password

Writes emails in files in emails/[folder's name]/.
"""
if __name__ == '__main__':
	with open('password', 'r') as content_file:
		content = content_file.read().strip().split(":")
		imap_server = content[0]
		login = content[1]
		password = content[2]
	connection = imaplib.IMAP4_SSL(imap_server)
	connection.login(login, password)

	folders = get_folders(connection)
	num_mail = 0
	for folder in folders:
		if not folder in ignore:
			print("%s:" % folder.upper())
			messages = retrieve_messages(connection, folder)
			if len(messages) >= 10:
				directory = os.path.join("emails", folder.replace('/', '__').replace(' ', '_'))
				if not os.path.exists(directory):
					os.makedirs(directory)

				for message in messages:
					subject = message[0]
					recipient = message[1]
					sender = message[2]
					mail_content = message[4]
					print(subject)
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
				print("Not enough mails to train.")

			print("")
			print("")
