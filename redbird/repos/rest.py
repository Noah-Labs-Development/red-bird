
import urllib.parse as urlparse
from typing import Any, Dict, Iterable, List, Optional, Union

from pydantic import BaseModel

from redbird.oper import GreaterEqual, GreaterThan, LessEqual, LessThan, NotEqual, Operation
from redbird.base import BaseResult, BaseRepo

import requests

from redbird.templates import TemplateRepo

class Session(requests.Session):
    """Subclassed requests.Session for more
    unified methods.
    """

    def remove(self):
        self.close()


class RESTRepo(TemplateRepo):

    """REST API Repository

    Parameters
    ----------
    url : str
        Base URL for the API. Should not contain
        query parameters or the item ID. The full
        URL will be "{url}/{id}" if a single item
        is searched, "{url}?{param}={value}" if 
        the endpoint is queried.
    headers : dict
        HTTP Headers (for example authentication)
    url_params : dict
        Additional query parameters passed to every 
        request.
    result : str, callable
        Where the list of items is found from the output.
    """
    result: Optional[Union[str, callable]]

    def __init__(self, *args, url, headers:dict=None, url_params:dict=None, result=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url
        self.session = Session()

        self.headers = headers
        self.url_params = {} if url_params is None else url_params
        self.result = result

    def insert(self, item):
        json = self.item_to_dict(item)
        self._request(
            "POST",
            self.url,
            json=json
        )

    def replace(self, item):
        qry = {self.id_field: self.get_field_value(item, self.id_field)}
        values = self.item_to_dict(item)
        self.filter_by(**qry).replace(**values)

    def _request(self, *args, **kwargs):
        page = self.session.request(
            *args, **kwargs, headers=self.headers
        )
        return page

    def query_read(self, query):
        url = query
        page = self._request("GET", url)
        output = page.json()

        result_loc = self.result
        if result_loc is None:
            items = output
        elif isinstance(result_loc, str):
            items = output[result_loc]
        elif isinstance(result_loc, callable):
            items = result_loc(output)
        else:
            raise TypeError(f"Could not locate results from {result_loc}")

        if isinstance(items, (list, tuple, set)):
            for data in items:
                yield data
        else:
            yield items

    def query_delete(self, query):
        url = query
        self._request("DELETE", url)

    def query_update(self, query, values):
        url = query
        self._request("PATCH", url, json=values)

    def query_replace(self, query, values):
        url = query
        self._request("PUT", url, json=values)

    def format_query(self, query:dict) -> str:
        "Turn the query to a form that's understandable by the underlying API"
        id = query.pop(self.id_field) if query is not None and self.id_field in query else None

        url_base = self.url
        url_params = self._get_url_params(query)

        # URL should look like "www.example.com/api/items/{id}?{param}={value}"
        # or "www.example.com/api/items/{id}"
        # or "www.example.com/api/items?{param}={value}"
        # or "www.example.com/api/items"
        if id and url_params:
            return f"{url_base}/{id}?{url_params}"
        elif id:
            return f"{url_base}/{id}"
        elif url_params:
            return f"{url_base}?{url_params}"
        else:
            return url_base

    def _get_url_params(self, query:dict) -> str:
        query = {} if query is None else query
        url_params = self.url_params.copy()
        url_params.update(query)
        return urlparse.urlencode(url_params)
