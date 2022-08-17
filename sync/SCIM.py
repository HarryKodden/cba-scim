from __future__ import print_function

import json
import logging
import requests
import base64

logger = logging.getLogger('root')

class SCIM(object):

  def __init__(self, server, bearer=None, verify=True, cacert=None):
    self.server = server
    self.bearer = bearer

    if verify and cacert:
      self.verify = cacert
    else:
      self.verify = verify

    self.groups = {}
    self.users = {}

    self.stats = { 
      'reads' : 0,
      'writes' : 0
    }

  def __enter__(self):
    for group in self.request('/Groups').get('Resources', []):
      self.groups[group['displayName']] = self.request(group['meta']['location'])

    for user in self.request('/Users').get('Resources', []):
      self.users[user['userName']] = self.request(user['meta']['location'])

    return self

  def __exit__(self, exception_type, exception_value, traceback):
    """ Nothing to do here """
    pass

  def __repr__(self):
      return json.dumps(self.json(), indent=4, sort_keys=True)

  def json(self):
      return {
          'users': self.users,
          'groups': self.groups
      }

  def request(self, uri, method='GET', payload=None):
    url = self.server + uri
    
    headers = {}

    if payload:
      headers['Content-Type'] = "Content-type: application/scim+json"

    if self.bearer:
      headers['Authorization'] = f"Bearer {self.bearer}"
    
    try:
      logger.debug(f"SCIM: {method} {url} {payload}")

      response = requests.request(method, url, data=json.dumps(payload), headers=headers, verify=self.verify)
      logger.debug(response.text)

      logger.debug(f"RC = {response.status_code}")

      if (response.status_code not in [200,201,204]):
        raise Exception(f"{method} on {url} data: {payload}: {response.status_code} Error: {response.text} ")

      logger.debug(f"[{response.status_code}] {method} {url}...")

      if method == 'GET':
        self.stats['reads'] += 1
      else:
        self.stats['writes'] += 1

      if (response.text > ''):
        return response.json()

    except requests.exceptions.SSLError:
      logger.error("SSL Validation error.")

    return None
  
  # Members...

  def get_members(self, groupName):
    return [ p['value'] for p in self.groups.get(groupName, {}).get('members', []) ]

  def set_members(self, groupName, new_members):
      patches = {
          "schemas": [ "urn:ietf:params:scim:api:messages:2.0:PatchOp" ],
          "Operations": []
      }
                  
      old_members = self.get_members(groupName)

      for userName in old_members:
        if userName not in new_members: 
          patches['Operations'].append({
              "op": "remove",
              "path": f"members[value eq \"{userName}\"]"
          })

        for userName in new_members:
          if userName not in old_members:
              patches['Operations'].append({
                  "op": "add",
                  "path": "members",
                  "value": [{
                      "value": f"{userName}" 
                  }]
              })

      if len(patches['Operations']) > 0:
          self.request(self.groups[groupName]['meta']['location'], method='PATCH', payload=patches)

      self.groups[groupName]['members'] = [ { 'value': m } for m in new_members ]

  # User...

  def get_user(self, userName):
    return self.users.get(userName, None)

  def set_user(self, userName, updates):
      
    patches = {
      "schemas": [ "urn:ietf:params:scim:api:messages:2.0:PatchOp" ],
      "Operations": []
    }
    
    for path, value in updates.items():

      operation = { 'path': path }

      if path in self.users[userName] and value and self.users[userName][path] != value:
        operation['op'] = "replace"
      elif path in self.users[userName] and not value:
        operation['op'] = "remove"
      elif path not in self.users[userName] and value:
        operation['op'] = "add"

      if 'op' in operation:
        if value:
          operation['value'] = value

        patches['Operations'].append(operation)

    if len(patches['Operations']) > 0:
      self.request(self.users[userName]['meta']['location'], method='PATCH', payload=patches)

  def add_user(self, userName, externalId = '', displayName = '', givenName = '', familyName = '', mail = [], certificates = []):

    my_emails = []
    for value in mail + [externalId]:
      
      email = { 'value': value }
      if len(my_emails) == 0:
          email['primary'] = True
      
      my_emails.append(email)

    my_name = {
      "givenName": givenName,
      "familyName": familyName
    }

    my_certificates = []
    for key in certificates:
      details = key.split()

      cert = {
        'type': details[0],
        'value' : base64.b64encode(details[1].encode()).decode()
      }
      if len(details) > 2:
        cert['display'] = details[2]

      my_certificates.append(cert)
      
    if userName not in self.users:

      payload = {
        'schemas':[
          'urn:scim:schemas:core:1.0'
        ],
        'externalId': externalId,
        'userName': userName,
        'active': True,
        'name': my_name,
        'emails': my_emails,
        'x509Certificates': my_certificates
      }

      if displayName:
        payload['displayName'] = displayName

      self.users['userName'] = self.request(
        self.request(
          '/Users', method='POST', payload=payload
        )['meta']['location']
      )

    else:

      self.set_user(userName, {
        'active': True,
        'displayName': displayName,
        'externalId': externalId,
        'name': my_name,
        'emails': my_emails,
        'x509Certificates': my_certificates
      })

  def del_user(self, userName):
    if userName in self.users:
      self.set_user(userName, {'active' : False} )

    for groupName in self.groups:
      members = self.get_members(groupName)
      if userName in members:
        members.remove(userName)
        self.set_members(groupName, members)

  # Group ...

  def get_group(self, groupName):
    return self.users.get(groupName, None)

  def add_group(self, groupName, members):

    if groupName not in self.groups:

      self.groups[groupName] = self.request(
        '/Groups', method='POST', payload={
          "schemas":[
                  "urn:scim:schemas:core:1.0"
              ],
              "displayName": f"{groupName}",
              "members": [ { 'value': m } for m in members ]
        }
      )['meta']['location']

    else:
      self.set_members(groupName, members)

  def del_group(self, groupName):
    self.request(self.groups[groupName]['meta']['location'], method='DELETE')

