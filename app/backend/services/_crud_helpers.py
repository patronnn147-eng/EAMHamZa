"""Shared query-building helpers for the CRUD-style service classes in this package.

Extracted from an identical `_apply_filters`/`_apply_sort` staticmethod pair that
had been copy-pasted verbatim into several service classes. Behavior-preserving
extraction only.
"""


def apply_filters(query, count_query, model, query_dict):
    """Apply equality filters from query_dict to both queries."""
    if not query_dict:
        return query, count_query
    for field, value in query_dict.items():
        if hasattr(model, field):
            condition = getattr(model, field) == value
            query = query.where(condition)
            count_query = count_query.where(condition)
    return query, count_query


def apply_sort(query, sort, model):
    """Apply ordering to query; defaults to id.desc()."""
    if not sort:
        return query.order_by(model.id.desc())
    if sort.startswith("-"):
        field_name = sort[1:]
        if hasattr(model, field_name):
            return query.order_by(getattr(model, field_name).desc())
    elif hasattr(model, sort):
        return query.order_by(getattr(model, sort))
    return query.order_by(model.id.desc())
