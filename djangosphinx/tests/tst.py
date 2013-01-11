#coding: utf-8

__author__ = 'ego'

from djangosphinx.db.source.sql import *
from djangosphinx.db.source.sql.fields import *
from djangosphinx.db.index.base import *


class YIndex(Index):

    source = SQLIndexSource('pgsql', '127.1', '9206', 'user', 'password', 'database')

    class Meta:
        docinfo = 'inline'

    text = Field(alias='txt_field')
    id = UIntField()

    slug = Field(stored=True)

    ft = Field(stored=True, fulltext=True)
