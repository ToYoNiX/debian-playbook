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


def parse_env_line(raw_line):
    """Return (key, value) for a KEY=VALUE line, or None for anything else
    (comments, blank lines, lines without a key)."""
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, _, value = stripped.partition("=")
    key = key.strip()
    if not key:
        return None
    return key, value.strip()


def parse_env_lines(lines):
    """Dict of key -> value for every KEY=VALUE line, the last one winning."""
    parsed = {}
    for raw_line in lines:
        entry = parse_env_line(raw_line)
        if entry:
            parsed[entry[0]] = entry[1]
    return parsed


def update_env_lines(lines, key, value, state):
    """Return (new_lines, changed). Only lines for key are touched, every
    other line (comments, blank lines, other keys) is kept exactly as it was.
    The first line for key is updated in place and any later duplicates are
    dropped. A missing key is appended at the end."""
    wanted = "{0}={1}".format(key, value) if state == 'present' else None
    new_lines = []
    changed = False
    seen = False

    for line in lines:
        entry = parse_env_line(line)
        if entry is None or entry[0] != key:
            new_lines.append(line)
            continue
        if wanted is None or seen:
            changed = True
            continue
        seen = True
        if entry[1] != value:
            changed = True
            line = wanted
        new_lines.append(line)

    if wanted is not None and not seen:
        new_lines.append(wanted)
        changed = True

    return new_lines, changed


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

    lines = [line.rstrip("\n") for line in raw_lines]
    new_lines, changed = update_env_lines(lines, key, value, state)

    result['before'] = parse_env_lines(lines)
    result['after'] = parse_env_lines(new_lines)
    result['changed'] = changed

    # Nothing to do — bail out before touching the filesystem.
    if not changed or module.check_mode:
        module.exit_json(**result)

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
