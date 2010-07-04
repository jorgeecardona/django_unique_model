from datetime import datetime
from django.db import models

# Create your models here.
from uuid import uuid4

class EntityNotFoundException(Exception):
    pass

class DuplicatedEntityException(Exception):
    pass

class ReferenceUniqueModel(models.CharField):

    description = "A reference to a unique model."

    __metaclass__ = models.SubfieldBase

    def __init__(self, class_, *args, **kwargs):
        self._class = class_
        kwargs['max_length'] = 36
        super(ReferenceUniqueModel, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if isinstance(value , UniqueModel):
            return value

        if isinstance(self._class, (str, unicode)):
            base, sub = self._class.rsplit('.',1)
            self._class = __import__(base, fromlist=[sub])

        try:
            return self._class._get_by(uuid=value)
        except:
            return None
        
    def get_prep_value(self, value):
        return value.uuid if isinstance(value, UniqueModel) else None

    # def get_prep_lookup(self, lookup_type, value):
    #     if lookup_type == 'exact':
    #         return self.get_prep_value(value)
    #     if lookup_type == 'isnull':
    #         return None
    #     else:
    #         raise TypeError('Lookup type %r not supported.' % (lookup_type))

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
#    timestamp_uuid = UniqueCombined(fields=['uuid'])
    timestamp_uuid = models.DateTimeField()

    @classmethod
    def _create(cls, __unique__fields__ = [], *args, **kwords):

        entity = cls(*args, **kwords)

        for i in xrange(10):

            uuid = str(uuid4())
            now = datetime.utcnow()

            entity.uuid = uuid
            for field in entity._meta.fields:
                if field.name.startswith('timestamp_'):
                    setattr(entity, field.name, now)
                
            entity.save()
            
            field_names = entity._meta.get_all_field_names()
            field_names = [name for name in field_names if name.startswith('timestamp_')]

            # Walk in all the fields.
            for name in field_names:
                
                # Get keys from field name
                keys = name.replace('timestamp_', '').split('_')
                
                # Get user
                parameters = dict([(k, getattr(entity, k)) for k in keys])
                user = cls._get_by(**parameters)

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
    def _get_by(cls, **kwargs):
        try:
            timestamp = 'timestamp_%s' % ('_'.join(kwargs.keys()))
            return cls.objects.filter(
                **kwargs
                  ).order_by(timestamp)[0]
        
        except IndexError:
            raise EntityNotFoundException(
                "Class: <%s>, %s." % (
                    cls.__name__, 
                    ', '.join(["%s: <%s>" % (k,v) for k,v in kwargs.items()])
                    )
                )

    def _update(self, **kwords):

        # Check if change is useless
        if all([getattr(self, k) == v for k,v in kwords.items()]):
            return self

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
