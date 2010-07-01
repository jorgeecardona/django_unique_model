from datetime import datetime
from django.db import models

# Create your models here.
from uuid import uuid4

class EntityNotFoundException(Exception):
    pass

class DuplicatedEntityException(Exception):
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

    uuid = models.CharField(max_length=36)
    timestamp_uuid = models.DateTimeField()

    @classmethod
    def _create(cls, __unique__fields__ = [], *args, **kwords):

        entity = cls(*args, **kwords)

        for i in xrange(10):

            uuid = str(uuid4())
            now = datetime.utcnow()

            entity.uuid = uuid
            for key in entity.__dict__.keys():
                if key.startswith('timestamp_'):
                    setattr(entity, key, now)
                
            entity.save()
            
            # Walk in all the fields.
            for field in entity._meta.fields:
                
                # Check for fields that starts with timestamp_
                if field.name.startswith('timestamp_'):
                    
                    # Get keys from field name
                    keys = field.name.replace('timestamp_', '').split('_')
                    
                    # Get user
                    user = cls._get_by(**dict([(k, getattr(entity, k)) for k in keys]))

                    # Check unique
                    if user != entity:
                        # There is a duplicated entity.
                        entity.delete()

                        if field.name == 'timestamp_uuid':
                            # If uuid, then try a new uuid
                            break

                        raise DuplicatedEntityException
    
            return entity

        raise Exception("Maximum number of tries reached.")
    
    @classmethod
    def create(cls, *args, **kwords):
        raise Exception("NonImplemented")

    @classmethod
    def get_by_uuid(cls, uuid):
        return cls._get_by(uuid=uuid)

    @classmethod
    def _get_by(cls, **kwords):
        try:
            timestamp = 'timestamp_%s' % ('_'.join(kwords.keys()))
            return cls.objects.filter(
                **kwords
                  ).order_by(timestamp)[0]
        
        except IndexError:
            raise EntityNotFoundException(
                "Class: <%s>, %s." % (cls.__name__, ', '.join(["%s: <%s>" % (k,v) for k,v in kwords.items()]))
                )

    def _update(self, **kwords):

        # Copy parameters from self
        names = self._meta.get_all_field_names()
        parameters = dict([(k, getattr(self, k)) for k in names])
        parameters.pop('id')

        # Change all dates, in order to preserve actual uniqueness.
        now = datetime.utcnow()
        timestamps = dict([(k, now) for k in names if k.startswith('timestamp_')])
        
        # Change fields
        parameters.update(kwords)
        parameters.update(timestamps)

        entity = self.__class__(**parameters)
        entity.save()
        
        for name in self._meta.get_all_field_names():
            if name.startswith('timestamp_'):
                keys = name.replace('timestamp_', '').split('_')
                if any([k in keys for k in kwords.keys()]):
                    confirm_entity = self.__class__._get_by(**dict([(k, parameters[k]) for k in keys]))
                    if confirm_entity != entity:
                        entity.delete()
                        raise DuplicatedEntityException
                    
        
        
        self.delete()
        return entity
            


#        parameters.update(timestamps)
        
        # Create entity.
#        entity = self.__class__(**parameters)
#        entity.save()
        
        
            


    def __eq__(self, other):
        if isinstance(other, UniqueModel):
            return (self.uuid == other.uuid)
        return False

    class Meta:
        abstract = True


from django import forms

class ReferenceField(forms.CharField):
    pass


#class UniqueField()
