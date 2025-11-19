def _update_keywords(collection, *keywords):
    collection["keywords"].extend(keywords)


def update_keywords_args(collection, arg1, arg2):
    _update_keywords(collection, arg1, arg2)


def update_keywords_kwargs(collection, kw1="test", kw2="test"):
    _update_keywords(collection, kw1, kw2)


def update_keywords_vkwargs(collection, **kwargs):
    _update_keywords(collection, kwargs["kw3"], kwargs["kw4"])
