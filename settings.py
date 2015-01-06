requests_schema = {
	'url' : {
		'type': 'string',
		'required': True
	},
	'depth': {
		'type': 'integer',
		'default': 0
	},
	'pid' : { # parent's _id in /pages
		'type': 'string',
		'default': ''
	}
}

requests_settings = {
	'item_title': 'request',
	'schema': requests_schema
}

pages_schema = {
	'url': {
		'type': 'string',
		'required': True
	},
	'url_final': {
		'type': 'string',
		'required': True
	},
	'url_hash': {
		'type': 'string',
		'required': True
	},
	'domain': {
		'type': 'string',
		'required': False,
		'default': ''
	},
	'data': {
		'required': True
	},
	'data_hash': {
		'type': 'string',
		'required': True
	},
	'depends': {
		'type': 'list',
		'required': False,
		'default': []
	},
	'depends_map': {
		'type': 'dict',
		'required': False,
		'default': {}
	}
}

pages_settings = {
	'item_title': 'page',
	#'additional_lookup': {
	#	'url': 'regex("[\w]+")',
	#	'field': 'url_hash'
	#},
	'schema': pages_schema
}

DOMAIN = {
	'requests': requests_settings,
	'pages': pages_settings
	}
MONGO_DBNAME = 'pyarc'
RESOURCE_METHODS = ['GET', 'POST']
ITEM_METHODS = ['GET']
