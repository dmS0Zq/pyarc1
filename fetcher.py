from urllib.request import urlopen
from urllib.request import Request
from urllib import parse
from hashids import Hashids
from bson.objectid import ObjectId
from bs4 import BeautifulSoup
from pymongo import MongoClient
import pymongo
import time
import json
import re
import hashlib
import base64
import datetime

client = MongoClient()
db = client.pyarc


def get_hash_code(string):
	#MOD = 1000000000000
	MOD = 1000000000000000
	MULT = 37
	hash_code = 0
	hash_code *= MULT
	hash_code += len(string)
	hash_code %= MOD
	for c in list(string):
		hash_code *= MULT
		hash_code += ord(c)
		hash_code %= MOD
	return hash_code

def url_seems_like_binary_file(url):
	p = re.compile('^.*?\.(jpg|jpeg|png|gif)$', re.IGNORECASE)
	return p.match(url) != None

def url_seems_like_text_file(url):
	p = re.compile('^.*?\.(html|htm|js|css|php|txt)$', re.IGNORECASE)
	return p.match(url) != None

def POST_new_document_to_pages(document_info):
	try:
		POST_page_data = json.dumps({
			'url': document_info['requested_url'],
			'url_final': document_info['final_url'],
			'url_hash': base58_hashids.encrypt(get_hash_code(document_info['requested_url'])),
			'domain': parse.urlparse(document_info['final_url'])[1], # [1] gets network location (netloc)
			'data': document_info['b64_data'].decode('utf-8'),
			'data_hash': document_info['data_hash'],
			'depends': [],
			'depends_map': {}
			}).encode('utf-8')
		POST_page_headers = {'Content-Type': 'application/json'}
		POST_request = Request("http://localhost:5000/pages", POST_page_data, POST_page_headers)
		POST_response = urlopen(POST_request)
		info = POST_response.info()
		data = POST_response.read()
		new_document_id = json.loads(data.decode('utf-8'))['_id']
		return new_document_id
		#print(info,data)
	except Exception as e:
		raise
	else:
		pass
	finally:
		pass

def POST_new_request(url, parent_id, depth):
	try:
		if db.requests.find({'url': url}).count() < 1:
			#print(datetime.datetime.utcnow() - datetime.timedelta(minutes=5))
			if db.pages.find({
				'_updated': {
					'$gt': datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
					},
				'url': url
				}).count() > 1:
				print("Would grab",url,"but recently got it")
			else:
				POST_request_data = json.dumps({
					'url': url,
					'pid': parent_id,
					'depth': depth
					}).encode('utf-8')
				POST_request_headers = {'Content-Type': 'application/json'}
				POST_request = Request("http://localhost:5000/requests", POST_request_data, POST_request_headers)
				POST_response = urlopen(POST_request)
				info = POST_response.info()
				data = POST_response.read()
				new_request_id = json.loads(data.decode('utf8'))['_id']
	except Exception as e:
		raise
	else:
		pass
	finally:
		pass

def add_depend_to_parent(parent_id, child_id, child_url_hash):
	parent_document = db.pages.find({ '_id': parent_id})
	if parent_document != None:
		db.pages.update(
			{'_id': parent_id},
			{ '$addToSet' : {
				'depends': child_id
				},
			'$set': {
				str('depends_map.'+child_url_hash): child_id
				}
			}
		)
	else:
		pass

base58_hashids = Hashids(alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')

while True:
	# extract one request from db.requests
	a_request = db.requests.find_one(
		fields={'url': True, 'depth': True, 'pid': True,'_id': True},
		sort=[("_created", pymongo.ASCENDING)]
	)
	# if there was one ...
	if a_request != None:
		# gather info from it for easy access
		request_info = {
			'requested_url': a_request['url'],
			'requested_depth': a_request['depth'],
			'parent_pages_id': a_request['pid']
		}
		try:
			# prepare to go on the internet and GET the request
			GET_request_headers = {'User-Agent': 'pyarc/alpha'}
			GET_request = Request(
				request_info['requested_url'],
				headers=GET_request_headers
			)
			# go on the internet
			GET_request_response = urlopen(request_info['requested_url'])
			# read in the raw data
			# at this point, we don't really know what we grabbed
			# the raw_data could be anything
			raw_data = GET_request_response.read()
			# gather up some info that we will want no matter what we fetched
			# we will add to this later too
			document_info = {
				'requested_url': request_info['requested_url'],
				'final_url': GET_request_response.geturl()
			}
			# basically, if it does not seem like a text file, we will not
			# want to try and find links inside of it if we have depth remaining
			if url_seems_like_binary_file(document_info['final_url']):
				# base64 encode the data and add to the info
				document_info['b64_data'] = base64.b64encode(raw_data)
				# also store the hash
				document_info['data_hash'] = hashlib.sha1(raw_data).hexdigest()
				# log whether or not this document has a parent
				if request_info['parent_pages_id'] == '':
					print("W: apparent binary file without parent")
				else:
					print("I: apprent binary file with parent",request_info['parent_pages_id'])
				# send the gathered document_info to that function that POSTs it
				# to /pages and returns the _id of the new document
				new_document_id = POST_new_document_to_pages(document_info)
			# here, we will treat the raw_data as a text file instead
			# hopefully this isn't a bad idea
			# instead of just trusting file extensions, we may want to find a
			# better way to determine data type
			else:
				# bsae64 encode the data
				# do it for consistancy in the database so that all data
				# elements are the same: base64 encoded
				document_info['b64_data'] = base64.b64encode(raw_data)
				# hey! Let's get that hash while we are at it
				document_info['data_hash'] = hashlib.sha1(raw_data).hexdigest()
				# still can't shut up about parent issues.
				if request_info['parent_pages_id'] == '':
					print("I: apparent text file without parent")
				else:
					print("I: apparent text file with parent",request_info['parent_pages_id'])
				# send the gathered document_info to that function that POSTs it
				# to /pages and returns the _id of the new document
				new_document_id = POST_new_document_to_pages(document_info)
				# remember that 'depth' stuff? Time to potentially go "recursive"
				# depth == -1 : that's it. Do not download anything more. Done.
				# depth ==  0 : only download embedded stuff.
				# depth >=  1 : download embedded stuff and linked-to stuff
				# default is probably 0. <-- wow get a load of this guy: "probably"
				if request_info['requested_depth'] >= 0:
					soup = BeautifulSoup(raw_data.decode('utf-8'))
					if request_info['requested_depth'] > 0:
						# find each unique <a> in html
						# though ... so far ... we never even verified this was
						# html instead of css, javascript, etc.
						for a in set(soup.find_all('a')):
							# convert a potentially relative URL in a['href'] to
							# an absolute URL, using info from
							# document_info['final_url'] if necessary
							full_href = parse.urljoin(document_info['final_url'], a['href'])
							# send the absolute URL, the parent of this URL,
							# and a decremented depth off to a function that
							# POSTs it to /requests!
							POST_new_request(full_href, new_document_id, request_info['requested_depth'] - 1)
						for link in set(soup.find_all('link')):
							full_href = parse.urljoin(document_info['final_url'], link['href'])
							POST_new_request(full_href, new_document_id, request_info['requested_depth'] - 1)
							pass
						# there may be links not found at this point
						# but right now I need to get this off the group and
						# functioning at a basic level
					# here, sinrequested_urlce depth is still >= 0, request that embedded stuff
					for img in set(soup.find_all('img')):
						# similarly, turn a possibly relative URL into a
						# absolute URL using document_info['final_url'] if needed
						img_src = parse.urljoin(document_info['final_url'], img['src'])
						# and send the absolute URL, the parent of this URL,
						# and a depth of -1 to the function that POSTs it to
						# requests. a depth of -1 is used because this is an
						# image and won't be the parent of anything.
						POST_new_request(img_src,new_document_id,-1)
					# again, there may very likely be more embedded, but the
					# project should get barely functional before worrying about
					# grabbing any more
			# if the document we grabbed has a parent, update the parent's info
			if request_info['parent_pages_id'] != '':
				#print("sending",document_info['requested_url'],base58_hashids.encrypt(get_hash_code(document_info['requested_url'])))
				add_depend_to_parent(ObjectId(request_info['parent_pages_id']),
					new_document_id,
					base58_hashids.encrypt(get_hash_code(document_info['requested_url']))
				)
		except Exception as e:
			print(e)
		else:
			pass
		finally:
			# no matter what happened up there, remove the request from the
			# queue of requests
			db.requests.remove(a_request['_id'])
			pass
	else:
		print(".")
		time.sleep(0.9)
	time.sleep(0.1)
