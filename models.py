from django.db import models

# Create your models here.
from uuid import uuid4

class EntityNotFoundException(Exception):
    pass

class UniqueModel(models.Model):
    """
    Unique Model
    ============

    This class defines an abstract class that permit to define uniquely an entity using
    uuid, and define the set and get of the class, and the creation process without lead to
    race conditions problems.

    ## Performance:

    The creation process is linear in the db size.

    """

    uuid = models.CharField(max_length=36, primary_key=True)
    uuid_timestamp = models.DateTimeField(auto_now_add=True)

    @classmethod
    def _create(cls, __unique__fields__ = [], *args, **kwords):

        entity = cls(*args, **kwords)

        for i in xrange(10):
            uuid = str(uuid4())
            entity.uuid = uuid
            entity.save()

            if cls.get_by_uuid(uuid) == entity:
                return entity

            entity.delete()

        raise Exception("Maximum number of tries reached.")
    
    @classmethod
    def create(cls, *args, **kwords):
        raise Exception("NonImplemented")

    @classmethod
    def get_by_uuid(cls, uuid):
        try:
            entity = cls.objects.filter(uuid = uuid).order_by('uuid_timestamp')[0]
            return entity

        except IndexError:
            raise EntityNotFoundException("Class: <%s>, uuid: <%s>." % (cls.__name__, uuid))

    class Meta:
        abstract = True


from django import forms

class ReferenceField(forms.CharField):
    pass


#class UniqueField()
