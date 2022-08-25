from __future__ import print_function

import json
import logging
import requests
import base64

logger = logging.getLogger(__name__)

class SCIM(object):

  def __init__(self, server, bearer=None, verify=True, cacert=None, broker = None):
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

    self.broker = broker
    self.services = {}

  def __enter__(self):
    for group in self.request('/Groups').get('Resources', []):
      self.get_group(group['id'])

    for user in self.request('/Users').get('Resources', []):
      self.get_user(user['id'])

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
      data = json.dumps(payload)
    else:
      data = None

    if self.bearer:
      headers['Authorization'] = f"Bearer {self.bearer}"
    
    try:
      response = requests.request(method, url, data=data, headers=headers, verify=self.verify)

      logger.debug(f"RC = {response.status_code}")

      if (response.status_code not in [200,201,204]):
        raise Exception(f"{method} on {url} data: {payload}: {response.status_code} Error: {response.text} ")

      logger.debug(f"[{response.status_code}] {method} {url}...")

      if method == 'GET':
        self.stats['reads'] += 1
      else:
        self.stats['writes'] += 1

      result = json.loads(response.text)
      logger.debug(result)
      return result

    except requests.exceptions.SSLError:
      logger.error("SSL Validation error.")
    except Exception as e:
      logger.error(f"SCIM Exception: {str(e)}")

    return None
  
  # Stats

  def get_stats(self):
    return { **self.stats, **self.services }
    
  # Broker & notifications...

  def add_service(self, service_name, service_pass):
    if not self.broker:
      raise Exception("No broker configured !")

    logger.debug(f"[SCIM] Add service '{service_name} to notifications to.")

    self.broker.enable_service(service_name, service_pass)
    self.services[service_name] = {}

  def notification(self, adjusted, topic, id):
    if not self.broker:
      raise Exception("No broker configured !")
      
    for service in self.services.keys():
      self.services[service].setdefault(topic, {})
      self.services[service][topic].setdefault(id, 0)

      logger.debug(f"[SCIM] Send to: {service}, topic: {topic}, id: {id}")

      if self.services[service][topic][id] > 0 and not adjusted:
        continue

      if self.broker.notify_service(service, { topic: id }):
        self.services[service][topic][id] += 1

  def user_notification(self, adjusted, name):
    self.notification(adjusted, 'user', self.users.get(name, {}).get('id', -1))

  def group_notification(self, adjusted, name):
    self.notification(adjusted, 'group', self.groups.get(name, {}).get('id', -1))

  # Members...

  def get_members(self, groupName):
    return [ p['value'] for p in self.groups.get(groupName, {}).get('members', []) ]

  def set_members(self, groupName, new_members):
      patches = {
          "schemas": [ "urn:ietf:params:scim:api:messages:2.0:PatchOp" ],
          "Operations": []
      }
                  
      old_members = self.get_members(groupName)

      for member in old_members:
        if member not in new_members: 
          patches['Operations'].append({
              "op": "remove",
              "path": f"members[value eq \"{member}\"]"
          })

        for member in new_members:
          if member not in old_members:
              patches['Operations'].append({
                  "op": "add",
                  "path": "members",
                  "value": [{
                      "value": f"{member}"
                  }]
              })

      self.groups[groupName]['members'] = [ { 'value': m } for m in new_members ]

      if len(patches['Operations']) > 0:
          self.request(self.groups[groupName]['meta']['location'], method='PATCH', payload=patches)
          return True

      return False

  # User...

  def get_user(self, id):
    user = self.request(f"/Users/{id}")
    self.groups[user['userName']] = user
    return user

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

      # Update my cache as well...        
      if value:
        self.users[userName][path] = value
      else:
        self.users[userName].pop(path, None)

    if len(patches['Operations']) > 0:
      self.request(self.users[userName]['meta']['location'], method='PATCH', payload=patches)
      return True

    return False

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

      self.users[userName] = self.request(
        self.request(
          '/Users', method='POST', payload=payload
        )['meta']['location']
      )

      adjusted = True
    else:
      adjusted = self.set_user(userName, {
          'active': True,
          'displayName': displayName,
          'externalId': externalId,
          'name': my_name,
          'emails': my_emails,
          'x509Certificates': my_certificates
        }
      )

    self.user_notification(adjusted, userName)

  def del_user(self, userName):
    adjusted = False

    if userName in self.users:
      adjusted = (self.set_user(userName, {'active' : False} ) or adjusted)

    id = self.users[userName]['id']

    for groupName in self.groups:
      members = self.get_members(groupName)
      
      if id in members:
        members.remove(id)
        adjusted = (self.set_members(groupName, members) or adjusted)

    self.user_notification(adjusted, userName)
      
  # Group ...

  def get_group(self, id):
    group = self.request(f"/Groups/{id}")
    self.groups[group['displayName']] = group
    return group
    
  def add_group(self, groupName, members):

    if groupName not in self.groups:

      group = self.request(
        '/Groups', method='POST', payload={
          "schemas":[
                  "urn:scim:schemas:core:1.0"
              ],
              "displayName": f"{groupName}",
              "members": [ { 'value': m } for m in members ]
        }
      )

      self.groups[groupName] = self.request(group['meta']['location'])

      adjusted = True
    else:
      adjusted = self.set_members(groupName, members)

    self.group_notification(adjusted, groupName)
        
  def del_group(self, groupName):
    self.request(self.groups[groupName]['meta']['location'], method='DELETE')
    self.groups.pop('groupName', None)
    self.group_notification(True, groupName)