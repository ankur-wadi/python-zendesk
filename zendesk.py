import requests, json

class Zendesk(object):
    def __init__(self, subdomain, auth, field_mapping={}, endpoint="https://{subdomain}.zendesk.com/api/v2"):
        self.subdomain, self.auth = subdomain, auth
        self.endpoint = endpoint.format(subdomain=subdomain)
        self.field_mapping = dict((v, k) for k, v in field_mapping.items())
        self.session = requests.session()
        
    def request(self, method, url, *args, **kwargs):
        if not url.startswith("http"): url = self.endpoint + url
        ret = self.session.request(method, url, auth=self.auth, *args, **kwargs)
        try:
            setattr(ret, 'json', json.loads(ret.content))
        except Exception, e: ret.json = None
        return ret
    
    def get(self, url, *args, **kwargs):
        return self.request('GET', url, *args, **kwargs) 
    
    def post(self, url, data, *args, **kwargs):
        kwargs['headers'] = kwargs.get('headers', {})
        kwargs['headers']['Content-Type'] = 'application/json'
        return self.request('POST', url, data=json.dumps(data), *args, **kwargs) 

    def put(self, url, data, *args, **kwargs):
        kwargs['headers'] = kwargs.get('headers', {})
        kwargs['headers']['Content-Type'] = 'application/json'
        return self.request('PUT', url, data=json.dumps(data), *args, **kwargs) 
   
    @property
    def fields(self):
        if not hasattr(self, '_fields'): self._fields = self._get_fields()
        return self._fields
    
    @property
    def id_fields(self):
        return dict((v['id'], v) for v in self.fields.values())
    
    def _get_fields(self):
        ret = self.get('/ticket_fields.json')
        fields = dict((self.field_mapping.get(e['title'], e['title']), e) for e in ret.json['ticket_fields'])
        if 'custom_field_options' in fields:
            fields['options'] = [o['value'] for o in fields['custom_field_options']]
        return fields
    
    def format_task_data(self, data):
        assert 'comment' in data, "must have a description"
        data['comment'] = data['comment'] if isinstance(data['comment'], dict) else {'body' : data['comment']}
        data['custom_fields'] = []
        fields = data.pop('fields', {})
        for k in fields.keys():
            if k not in self.fields: continue
            v = fields[k]
            assert ('options' not in self.fields[k]) or (v in self.fields[k]['options'])
            data['custom_fields'].append({'id' : self.fields[k]['id'], 'value' : v})
        return data

    def update_ticket_status(self, ticket_id, status, comment):
        return self.put("/tickets/%s.json" % ticket_id, {'ticket':{'status' : status, 'comment' : {'body': comment}}})

    def add_tags(self, ticket_id, tags):
        tags = [tags] if isinstance(tags, basestring) else tags
        return self.put("/tickets/%s/tags.json" % ticket_id, {'tags':tags})

    def list_tickets(self, view_id):
        ret = self.get("/views/%s/tickets.json" % view_id)
        return ret.json
    
    def create_task(self, **data):
        data = self.format_task_data(data)
        data['type'] = 'task'
        return self.post('/tickets.json', {'ticket' : data})


