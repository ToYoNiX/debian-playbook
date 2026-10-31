#!/usr/bin/python

# Copyright: (c) 2026, Assem Mohamed <toyonix.assemmohamed.2005@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: environment_kv

short_description: Manage key=value entries in /etc/environment (or similar env files) idempotently

version_added: "1.0.0"

description:
    - Parses a KEY=VALUE style file (like /etc/environment), updates the value of a
      given key if it already exists, adds it if it doesn't, or removes it entirely.
    - Unlike a naive C(echo >> file) approach, this never creates duplicate keys and
      only reports C(changed) when the file content actually changes.

options:
    path:
        description: Path to the environment-style file to manage.
        required: false
        type: str
        default: /etc/environment
    key:
        description: The environment variable name to set or remove.
        required: true
        type: str
    value:
        description: The value to set for O(key). Required when O(state=present).
        required: false
        type: str
    state:
        description: Whether the key should be present with the given value, or absent.
        required: false
        type: str
        choices: [present, absent]
        default: present
    backup:
        description: Create a timestamped backup of the file before changing it.
        required: false
        type: bool
        default: false

author:
    - Assem Mohamed (@ToYoNiX)
'''

EXAMPLES = r'''
- name: Ensure _JAVA_AWT_WM_NONREPARENTING is set to 1
  become: yes
  environment_kv:
    key: _JAVA_AWT_WM_NONREPARENTING
    value: "1"

- name: Set a variable in a custom env file with a backup
  environment_kv:
    path: /etc/environment
    key: MY_VAR
    value: "hello world"
    backup: true

- name: Remove a variable entirely
  become: yes
  environment_kv:
    key: SOME_OLD_VAR
    state: absent
'''

RETURN = r'''
path:
    description: The file that was managed.
    type: str
    returned: always
    sample: /etc/environment
backup_file:
    description: Name of the backup file created, if any.
    type: str
    returned: when backup=true and a change was made
before:
    description: Dict of key/value pairs found before the change.
    type: dict
    returned: always
after:
    description: Dict of key/value pairs after the change.
    type: dict
    returned: always
'''

import os
from ansible.module_utils.basic import AnsibleModule


def parse_env_lines(lines):
    """Turn a list of raw file lines into an ordered dict of key -> value,
    preserving any lines that aren't valid KEY=VALUE pairs as-is (comments,
    blank lines) in a separate passthrough list keyed by their position.
    """
    parsed = {}
    order = []  # preserves first-seen order of keys
    passthrough = []  # (index, raw_line) for lines we don't touch

    for idx, raw_line in enumerate(lines):
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        if not stripped or stripped.startswith("#") or "=" not in stripped:
            passthrough.append((idx, line))
            continue

        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()

        if not key:
            passthrough.append((idx, line))
            continue

        if key not in parsed:
            order.append(key)
        parsed[key] = value

    return parsed, order, passthrough


def render_env_lines(parsed, order):
    """Render dict back into KEY=VALUE lines, keeping original key order,
    with any newly added keys appended at the end."""
    lines = []
    for key in order:
        lines.append("{0}={1}".format(key, parsed[key]))
    return lines


def run_module():
    module_args = dict(
        path=dict(type='str', required=False, default='/etc/environment'),
        key=dict(type='str', required=True),
        value=dict(type='str', required=False, default=None),
        state=dict(type='str', required=False, default='present', choices=['present', 'absent']),
        backup=dict(type='bool', required=False, default=False),
    )

    result = dict(
        changed=False,
        path='',
        before={},
        after={},
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[('state', 'present', ['value'])],
    )

    path = module.params['path']
    key = module.params['key']
    value = module.params['value']
    state = module.params['state']
    backup = module.params['backup']

    result['path'] = path

    # Read existing content (treat a missing file as empty, matching typical
    # /etc/environment bootstrap scenarios).
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                raw_lines = f.readlines()
        except IOError as e:
            module.fail_json(msg="Failed to read {0}: {1}".format(path, str(e)))
    else:
        raw_lines = []

    parsed, order, passthrough = parse_env_lines(raw_lines)
    result['before'] = dict(parsed)

    changed = False

    if state == 'present':
        if parsed.get(key) != value:
            changed = True
        if key not in parsed:
            order.append(key)
        parsed[key] = value
    else:  # absent
        if key in parsed:
            del parsed[key]
            order = [k for k in order if k != key]
            changed = True

    result['after'] = dict(parsed)
    result['changed'] = changed

    # Nothing to do — bail out before touching the filesystem.
    if not changed:
        module.exit_json(**result)

    if module.check_mode:
        module.exit_json(**result)

    new_lines = render_env_lines(parsed, order)
    new_content = "\n".join(new_lines) + ("\n" if new_lines else "")

    if backup and os.path.exists(path):
        result['backup_file'] = module.backup_local(path)

    try:
        with open(path, 'w') as f:
            f.write(new_content)
    except IOError as e:
        module.fail_json(msg="Failed to write {0}: {1}".format(path, str(e)), **result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
