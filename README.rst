Cueillette
==========

Outline
~~~~~~~

1. `Overview <https://github.com/ducdetronquito/cueillette#overview>`_
2. `Installation <https://github.com/ducdetronquito/cueillettes#installation>`_
3. `Usage <https://github.com/ducdetronquito/cueillette#usage>`_
4. `License <https://github.com/ducdetronquito/cueillette#license>`_


Overview
~~~~~~~~

**Cueillette** is a low-level library, inspired by `RSS-Bridge <https://github.com/RSS-Bridge/rss-bridge>`_,
that aims to provide a read-only access to the content of websites having a fucking proprietary API,
or websites who haven't any.

It basically scraps website's HTML content and converts it into a python ``dict``.

⚠️ **Cueillette** encourages you to free data that are **public**. I won't add any tools
to scrap data that requires an authenticated access.


Installation
~~~~~~~~~~~~

**Cueillette** is a Python3-only module that you can install via ``pip``

.. code:: sh

    pip3 install cueillette
    

This package has the following dependecies:

* `lxml <https://github.com/lxml/lxml>`_
* `ujson <https://github.com/esnme/ultrajson>`_
* `requests <https://github.com/requests/requests>`_


Usage
~~~~~

.. code:: python
    
    from cueillette import facebook
    
    posts = facebook.posts.get('bhuphusis', '2017-06-12', 1)
    print(posts[0])
    {
        'publication_date': 'dimanche 11 juin 2017, 00:48',
        'media': {
            'type': 'facebook video',
            'url': 'https://facebook.com/bhuphusis/videos/1049238988544164/',
            'title': '« La peur est une formidable stratégie politique »'
        },
        'text_content': """
            « Les prolétaires n'ont rien à perdre que leurs chaînes.  Ils ont un monde à y gagner. »
            Manifeste Communiste, 1848
            Source: https://tinyurl.com/yd97tqxb
        """, 
        'publication_timestamp': '1497167302',
        'author': 'BHÛ',
        'url': 'https://facebook.com/bhuphusis/videos/1049238988544164/'
    }


License
~~~~~~~

**Cueillette** is released into the **Public Domain**. 🎉

Ps: If we meet some day, and you think this small stuff worths it, you
can give me a beer, a coffee or a high-five in return: I would be really
happy to share a moment with you ! 🍻
