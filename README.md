# debian-playbook

My Ansible Playbook for Debian! This project is reminiscent of another project I worked on [here](https://github.com/ToYoNiX/debian-project). Back in the day, I didn't know what I was doing and it was mostly for fun. However, It tought me a lot and put me on the direction I am on now. I want this one to be something permanent, something that I could put to test and improve upon, and finally something to put my knowledge to the test!

# My Goal

My goal here is to create a playbook that I can use for maintaining debian systems, install and configure them as I would like, and also help me to grasp ansible more.

# Layout

```
inventory/
  hosts.yaml        groups (categories) and the hosts in them
  group_vars/       settings per category, all/ applies everywhere
  host_vars/        settings per host
roles/              one role per feature, its options in defaults/main.yaml
playbooks/          one playbook per category, applies roles to that group
site.yaml           imports every category playbook in dependency order
library/            custom modules
```

Categories: `desktop` (with `gnome` and `dwl` under it), `power` (with `laptop` and `server` under it), `nvidia`, `notetaking`, `gaming`, `development`, `docker` and `virtualization` (with `passthrough` under it). A host can be in as many as it needs.

Roles that need ports open declare them in their defaults and open them through the `firewall` role, so a port is only open on hosts that run that role.

# Usage

```bash
ansible-galaxy collection install -r requirements.yaml

ansible-playbook site.yaml                     # everything, every host
ansible-playbook site.yaml --limit hoopoe      # everything one host needs
ansible-playbook playbooks/gaming.yaml         # one category
ansible-playbook playbooks/maintenance.yaml    # upgrades and cleanup
```

# Contribution

I am open for any contribution, from a simple bug fix all the way up to a full feature implementation! Just create a fork, do you stuff then open a pull request! Look for issues if you don't know what to do.
