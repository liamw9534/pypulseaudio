************
pypulseaudio
************

.. image:: https://pypip.in/version/pypulseaudio/badge.png?update
    :target: https://pypi.python.org/pypi/pypulseaudio/
    :alt: Latest PyPI version

.. image:: https://pypip.in/download/pypulseaudio/badge.png?update
    :target: https://pypi.python.org/pypi/pypulseaudio/
    :alt: Number of PyPI downloads

.. image:: https://travis-ci.org/liamw9534/pypulseaudio.png?branch=master
    :target: https://travis-ci.org/liamw9534/pypulseaudio
    :alt: Travis CI build status

.. image:: https://coveralls.io/repos/liamw9534/pypulseaudio/badge.png?branch=master
   :target: https://coveralls.io/r/liamw9534/pypulseaudio?branch=master
   :alt: Test coverage

A python library wrapper for interacting with the pulseaudio sound system.


Installation
============

Install the python library by running:

    pip install pypulseaudio


Documentation
=============

Documentation is hosted at https://pythonhosted.org/pypulseaudio



Project resources
=================

- `Source code <https://github.com/liamw9534/pypulseaudio>`_
- `Issue tracker <https://github.com/liamw9534/pypulseaudio/issues>`_
- `Download development snapshot <https://github.com/liamw9534/pypulseaudio/archive/master.tar.gz#egg=pypulseaudio-dev>`_


Changelog
=========

v0.1.0
------

Initial release supporting:

- Connection management with ``connect()`` and ``disconnect()``
- Enumerate installed audio cards using ``get_card_info_list()``, ``get_card_info_by_name()`` and ``get_card_info_by_index()``
- Enumerate available audio sources using ``get_source_info_list()``, ``get_source_info_by_name()`` and ``get_source_info_by_index()``
- Enumerate available audio sinks using ``get_sink_info_list()``, ``get_sink_info_by_name()`` and ``get_sink_info_by_index()``
- Enumerate installed modules using ``get_module_info_list()`` and ``get_module_info()``
- Module management with ``load_module()`` and ``unload_module()``
- Set a card's profile with ``set_card_profile_by_index()`` or ``set_card_profile_by_name()``

This release is intended to provide the main audio management functions only, rather than
audio streaming or sound sampling functions.
