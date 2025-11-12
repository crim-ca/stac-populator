def _extra_property(item, name, value):
    item["properties"][name] = value


def extra_property_args(item, args_name, args_value):
    _extra_property(item, args_name, args_value)


def extra_property_kwargs(item, kwargs_name="test", kwargs_value="test"):
    _extra_property(item, kwargs_name, kwargs_value)


def extra_property_vkwargs(item, **kwargs):
    _extra_property(item, name=kwargs.get("vkwargs_name"), value=kwargs.get("vkwargs_value"))
