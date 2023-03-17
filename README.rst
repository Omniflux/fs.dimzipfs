fs.dimzipfs
===========

``fs.dimzipfs`` is a PyFileSystem2 interface for DAZ Install Manager packages.

The exposed filesystem is as defined in Manifest.dsx, not the zipfile.

Supported Python versions
-------------------------

- Python 3.11

Usage
-----

.. code:: python

    >>> from fs.dimzipfs import DIMZipFS

    >>> DIMZipFS('IM00013176-02_DAZStudio421Win64bit.zip').listdir('')
    ....
    ['Application[PC-64-DAZ Studio-4.5]', 'Temp[PC-64]']

    >>> DIMZipFS('IM00013176-42_DefaultResourcesforDAZStudio420.zip').opendir('Content').listdir('')
    ....
    ['data', 'Light Presets', 'Props', "ReadMe's", 'Render Presets', 'Runtime', 'Scenes', 'Scripts', 'Shader Presets']

License
-------

This module is published under the MIT license.