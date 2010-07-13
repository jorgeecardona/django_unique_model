from datetime import datetime
from django.db import models

# Create your models here.
from uuid import uuid4

class UniqueField(models.DateTimeField):
    
    description = "Lock time to mantain uniqueness in a set of fields."
    
    __metaclass__ = models.SubfieldBase

    def __init__(self, fields, *args, **kwargs):
        if not isinstance(fields, list):
            fields = [fields]
        self.fields = fields
        super(UniqueField, self).__init__(*args, **kwargs)    


class EntityNotFoundException(Exception):
    pass

class DuplicatedEntityException(Exception):
    pass

class UniquenessException(Exception):
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
            # If _class is a string, the module has to be loaded.
            base, sub = self._class.rsplit('.',1)
            self._class = getattr(__import__(base, fromlist=[sub]), sub)

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
    _uniqueness_uuid = UniqueField('uuid')

    @classmethod
    def _create(cls, __unique__fields__ = [], *args, **kwords):

        entity = cls(*args, **kwords)

        for i in xrange(10):

            uuid = str(uuid4())
            now = datetime.utcnow()

            entity.uuid = uuid

            for field in entity._meta.fields:
                if isinstance(field, UniqueField):
                    setattr(entity, field.name, now)
                
            entity.save()
            
            for field in entity._meta.fields:
                if not isinstance(field, UniqueField):
                    continue
                
                # parameters
                parameters = dict([(k, getattr(entity, k)) for k in field.fields])
                result = cls._get_by(**parameters)
                
                if result != entity:
                    entity.delete()

                    if field.fields == ['uuid']:
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
        # Search for the right lock.
        for field in cls._meta.fields:
            if not isinstance(field, UniqueField):
                continue
            
            # Check if all the fields belong to a particular lock.
            if all([key in field.fields for key in kwargs.keys()]):
                entity = cls.objects.filter(**kwargs).order_by(field.name)
                if len(entity) > 0:
                    return entity[0]
                
                raise EntityNotFoundException("Entity no found for class: %s with arguments %s." % (
                        cls.__name__,
                        ', '.join(['%s = %s' % (k,v) for k,v in kwargs.items()])
                        ))

        raise UniquenessException("Lock not found for the sets of arguments.")


    def _update(self, **kwords):

        # Check if change is useless
        if all([getattr(self, k) == v for k,v in kwords.items()]):
            return self

        # Copy parameters from self
        parameters = dict([(field.name, getattr(self, field.name)) for field in self._meta.fields])
        parameters.pop('id')

        # Change all dates, in order to preserve actual uniqueness.
        now = datetime.utcnow()
        uniqueness = dict(
            [(field.name, now) for field in self._meta.fields if isinstance(field, UniqueField)]
            )
        
        # Change fields
        parameters.update(kwords)
        parameters.update(uniqueness)

        entity = self.__class__(**parameters)
        entity.save()
        
        for field in self._meta.fields:
            if not isinstance(field, UniqueField):
                continue

            if any([k in field.fields for k in kwords.keys()]):
                confirm_entity = self._get_by(**dict([(k, parameters[k]) for k in field.fields]))
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
