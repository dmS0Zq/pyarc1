from hashids import Hashids
from eve import Eve
from flask import send_file
from pymongo import MongoClient
from bs4 import BeautifulSoup
from urllib import parse
from bson.objectid import ObjectId
import pymongo
import base64
import magic
import io

base58_hashids = Hashids(alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')

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

mongo_client = MongoClient()
db = mongo_client.pyarc

app = Eve()

known_text = [
	'text/html',
	'text/javascript',
	'text/css',
	'text/plain'
]
known_image = [
	'image/gif',
	'image/jpeg',
	'image/png'
]

def determine_generic_file_type(raw_data):
	file_type = determine_full_mime_type(raw_data)
	if file_type in known_text:
		return 'text'
	elif file_type in known_image:
		return 'image'
	else:
		print("didn't find",file_type)
		return file_type

def determine_full_mime_type(raw_data):
	return magic.from_buffer(raw_data, mime=True).decode('utf-8')

@app.route('/render/<page_id>')
def render(page_id):
	try:
		page = db.pages.find_one(
			{'_id': ObjectId(page_id)},
			#fields={'data': True, 'depends_map': True},
			sort=[("_created", pymongo.DESCENDING)]
		)
		if page != None:
			raw_data = base64.b64decode(page['data'])
			file_type = determine_generic_file_type(raw_data)
			if file_type == 'text':
				file_type = determine_full_mime_type(raw_data)
				if file_type == 'text/html':
					soup = BeautifulSoup(raw_data)
					for a in soup.find_all('a'):
						for page_url in set([page['url'], page['url_final']]):
							url_hash = base58_hashids.encrypt(get_hash_code(parse.urljoin(page_url, a['href'])))
							if url_hash in page['depends_map']:
								child_page = db.pages.find_one({'_id': ObjectId(page['depends_map'][url_hash])})
								if child_page != None:
									a['href'] = str(child_page['_id'])
									break
					for link in soup.find_all('link'):
						for page_url in set([page['url'], page['url_final']]):
							url_hash = base58_hashids.encrypt(get_hash_code(parse.urljoin(page_url, link['href'])))
							if url_hash in page['depends_map']:
								child_page = db.pages.find_one({'_id': ObjectId(page['depends_map'][url_hash])})
								if child_page != None:
									link['href'] = str(child_page['_id'])
									break
					for img in soup.find_all('img'):
						for page_url in set([page['url'], page['url_final']]):
							url_hash = base58_hashids.encrypt(get_hash_code(parse.urljoin(page_url, img['src'])))
							if url_hash in page['depends_map']:
								child_page = db.pages.find_one({'_id': ObjectId(page['depends_map'][url_hash])})
								if child_page != None:
									img['src'] = str(child_page['_id'])
									break
					return soup.prettify()
				else:
					return raw_data
			elif file_type == 'image':
				return send_file(io.BytesIO(raw_data))
			else:
				return 'Don\'t know how to handle a file type of ' + file_type

			#return send_file(io.BytesIO(base64.b64decode(page['data'])))
			#return send_file(base64.b64decode(page['data']))

		else:
			#return 'Not going to do it. You can\'t make me'
			pass
	except Exception as e:
		print(e)
		#raise
	return 'Bad stuff happened'

if __name__ == '__main__':
	app.run()
