Summary
===========

**python-lkvm** is a python wrapper for lkvm command line which exposes its
methods through a simple API.  This allows other python applications to manage
instances.


Getting started
---------------

As most of python modules, *python-lkvm* can be installed via setuptools: ::

  $ python setup.py install

Once this module is installed, it can be used their method creating a client
instance, for example, for listing existing instances: ::

  import lkvm

  client = lkvm.Client()

  for ins in client.list_instances():
      print ins.name, ins.state
