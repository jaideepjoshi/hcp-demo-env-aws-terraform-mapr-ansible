#!/usr/bin/python

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: mapr_entity

short_description: This module manages MapR accountable entities

version_added: "2.4"

description:
    - "This module manages MapR accountable entities"

options:
    name:
        description:
            - Volume name
        required: true
    state:
        description:
            - state can be present/absent - default: present
        required: false
    topology:
        description:
            - Volume topology - default: /data
        required: false
    path:
        description:
            - Mount path of volume, if not set the volume will be unmounted.
        required: false
    read_ace:
        description:
            - Read ACE of the volume - default: p
        required: false
    write_ace:
        description:
            - Write ACE of the volume - default: p
        required: false
    min_replication:
        description:
            - Minimum replication of the volume - default: 2
        required: false
    replication:
        description:
            - Replication of the volume - default: 3
        required: false
    soft_quota_in_mb:
        description:
            - Advisory quota in MB. Zero value means no quota. - default: 0
        required: false
    hard_quota_in_mb:
        description:
            - Hard quota in MB. Zero value means no quota. - default: 0
        required: false
    read_only:
        description:
            - If the volume is read only - default: False
        required: false                
    accountable_entity_type:
        description:
            - Accountable entity type (user/group) - default: user
        required: false 
    accountable_entity_name:
        description:
            - Name of accountable entity - default: User which executes the script
        required: false 
author:
    - Carsten Hufe chufe@mapr.com
'''

EXAMPLES = '''
# Pass in a message
- name: Modify MapR entity
  mapr_entity:
    name: mapr
    type: user
    email: abc@email.com
    soft_quota_in_mb: 1024
    hard_quota_in_mb: 1024
'''

RETURN = '''
original_message:
    description: The original name param that was passed in
    type: str
message:
    description: The output message that the sample module generates
'''

from ansible.module_utils.basic import AnsibleModule
import subprocess
import json
import getpass

def run_module():
    # define the available arguments/parameters that a user can pass to
    # the module
    module_args = dict(
        type=dict(type='str', required=True),
        name=dict(type='str', required=True),
        email=dict(type='str', required=False, default=''),
        soft_quota_in_mb=dict(type='int', required=False, default='0'),
        hard_quota_in_mb=dict(type='int', required=False, default='0')
    )

    result = dict(
        changed=False,
        original_message='No changes',
        message='No changes'
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    entity_info = get_entity_info(module.params['type'], module.params['name'])
    if entity_info == None:
        module.fail_json(msg="Accountable entity " + module.params['name'] + " does not exist.", **result)

    new_values = dict(
        name = module.params['name'],
        type = module.params['type'],
        email = module.params['email'],
        soft_quota_in_mb = module.params['soft_quota_in_mb'],
        hard_quota_in_mb = module.params['hard_quota_in_mb']
    )

    old_values = dict(
        name = entity_info['EntityName'].encode('ascii','ignore'),
        type = "user" if int(entity_info['EntityType']) == 0 else 'group',
        email = (entity_info['EntityEmail'].encode('ascii','ignore') if 'EntityEmail' in entity_info else ''),
        soft_quota_in_mb = int(entity_info['EntityAdvisoryquota']),
        hard_quota_in_mb = int(entity_info['EntityQuota'])
    )

    for key in set(old_values.keys() + new_values.keys()):
        if old_values[key] != new_values[key]:
            result['changed'] = True
            result['original_message'] = "Entity " + module.params['name'] + " exists - values updated"
            result['message'] = result['original_message']
            break
    result['diff'] = dict()
    result['diff']['before'] = str(old_values)
    result['diff']['after'] = str(new_values)


    if not module.check_mode and result['changed']:
        # execute changes
        execute_entity_changes(new_values['type'], new_values['name'], new_values)

    module.exit_json(**result)

def get_entity_info(type, name):
    converted_type = "0" if type == "user" else "1"
    process = subprocess.Popen("maprcli entity info -name " + name + " -type " + converted_type + " -json", shell=True, stdout=subprocess.PIPE)
    entity_info = process.communicate()
    maprclijson = json.loads(entity_info[0])
    if 'data' in maprclijson:
        return maprclijson['data'][0]
    else:
        return None

def execute_entity_changes(type, name, new_values):
    update_cmd = "maprcli entity modify"
    update_cmd += " -type " + ("0" if type == "user" else "1")
    update_cmd += " -name " + name
    update_cmd += " -email '" + new_values['email'] + "'"
    update_cmd += " -advisoryquota " + str(new_values['soft_quota_in_mb'])
    update_cmd += " -quota " + str(new_values['soft_quota_in_mb'])
    subprocess.check_call(update_cmd, shell=True)

def main():
    run_module()

if __name__ == '__main__':
    main()