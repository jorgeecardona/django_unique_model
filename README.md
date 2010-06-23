
# Unique Model

This is an application that define a model with an unique field (uuid) with a private method that create elements of its type (_create), a method to get an entity based on the uuid (get_by_uuid).

## Uniqueness

Uniqueness is assured with a free lock method, using a uuid_timestamp field to order elements in get_by_uuid, and it assure that only the oldest element is returned, and if sometimes two elements are created with the same uuid the latest will be deleted at the creation method.