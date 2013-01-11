#coding: utf-8

from __future__ import absolute_import
from __future__ import unicode_literals

from .builder.generic import Builder as GenericBuilder

__author__ = 'ego'



class Config(object):

    def __init__(self, model, builder=None):
        self.model = model

        builder = builder or GenericBuilder
        self.builder = builder(model)

    def build(self):
        pass

    def render(self):
        return ''
