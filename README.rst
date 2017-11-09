Dream Dtb
=========

A dream journal system build around neovim

|gui|

Features
--------

-  Neovim is the main window of the gui and allows to comfortably write the body of the dream
-  Dreams are stored into an sqlite database with the following attributes:
        - title
        - date
        - text
        - list of tags
        - dream type (e.g: normal, lucid, ...)
-  New dreams can be added to the database
-  Navigation tree to quickly open and edit a dream

TODO
----

-  upload on pypi for easier installation
-  generate a pdf from the database
-  browse dream database on a web browser like a blog
-  add a dream from the command line
-  allow to modify tags, dreamtype, title, date of a dream
-  allow to remove a dream from the database
-  zsh completion script

.. |gui| image:: screenshot.png
