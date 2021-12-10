import json
from functools import wraps

import requests
from requests_toolbelt.utils.dump import dump_all  # TODO: remove it

REST_API_URL = "http://sandbox-t1.sat.is"


class SatisAPI:
    REST_API_URL = REST_API_URL

    def __init__(self, currency_list, disabled_pairs, auth=None):
        self.auth = auth
        self.debug_mode = True  # TODO: remove it
        self.currency_list = currency_list
        self.disabled_pairs = disabled_pairs

    @staticmethod
    def send_requests(method, api, *, debug=False, **kwargs):  # TODO: remove the debug
        """
        send api requests
        If show, print http header
        If debug_mode, print http header if not ok response
        """
        url = SatisAPI.REST_API_URL + api
        response = requests.request(method, url, **kwargs)

        # TODO: remove the show part
        if debug:
            print(dump_all(response).decode("utf-8"))

        try:
            return_json = json.loads(response.text)
        except Exception as e:
            raise (e)

        return return_json

    def _send_requests(self, method, api, auth_required=False, *, debug=False, **kwargs):  # TODO: remove the debug
        """
        provide the auth for the private APIs.
        """
        if auth_required:
            if not self.auth:
                raise Exception("No auth is found.")
            return self.send_requests(method, api, auth=self.auth, debug=self.debug_mode,
                                      **kwargs)  # TODO: remove the debug
        else:
            return self.send_requests(method, api, debug=self.debug_mode, **kwargs)  # TODO: remove the debug

    def _numeric_decorator(func):
        """ use this decorator can convert the result from str to int/float if it can"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            return SatisAPI.to_numeric_response(result)

        return wrapper

    @classmethod
    def to_numeric_response(cls, response):
        """
        convert all numeric result to int or float
        """

        def _str_numeric_converter(str_):
            if not isinstance(str_, str):
                return str_

            result = str_
            try:
                try:
                    result = int(str_)
                except:
                    result = float(str_)
            except:
                # it can't be int or float
                pass
            return result

        def _dict_to_numeric(dict_):
            for k, v in dict_.items():
                if isinstance(v, str):
                    dict_[k] = _str_numeric_converter(v)
                elif isinstance(v, list):
                    dict_[k] = cls.to_numeric_response(v)

        if isinstance(response, dict):
            _dict_to_numeric(response)
        elif isinstance(response, list):
            if not response:
                return response
            if isinstance(response[0], dict):
                for i in response:
                    _dict_to_numeric(i)
            elif isinstance(response[0], list):
                response = [[_str_numeric_converter(i) for i in sub_list] for sub_list in response]
            return response
        return response

    @_numeric_decorator
    def get_products(self):
        """
        GET the products info
        """
        api = "/api/products"
        return self._send_requests("GET", api)

    @_numeric_decorator
    def get_accounts_all(self):
        """
        GET the account balance 
        """
        api = "/api/accounts"
        return self._send_requests("GET", api, auth_required=True)

    @_numeric_decorator
    def get_trading_fees(self):
        """
        GET the trading fees 
        """
        api = "/api/fees"
        return self._send_requests("GET", api, auth_required=True)

    def post_order(self, product_id, side, size, order_type, price=None, reduce_only=None):
        api = "/api/orders"

        json = {
            "product_id": product_id,
            "side": side,
            "size": size,
            "type": order_type,
            "price": price,
            "reduce_only": reduce_only,
        }
        return self._send_requests("POST", api, auth_required=True, json=json)

    def post_limit_order(self, product_id, side, size, price, reduce_only=None):
        return self.post_order(product_id, side, size, "limit", price, reduce_only)

    def post_market_order(self, product_id, side, size, reduce_only=None):
        return self.post_order(product_id, side, size, "market", None, reduce_only)

    def del_user_order(self, order_id=None, product_id=None):
        api = f"/api/orders{'/' + order_id if order_id else ''}"

        querystring = {"product_id": product_id}

        return self._send_requests("DELETE", api, auth_required=True, params=querystring)

    @_numeric_decorator
    def get_position(self, product_id):
        api = f"/api/positions/{product_id}"
        return self._send_requests("GET", api, auth_required=True)

    @_numeric_decorator
    def post_position_risk(self, limit, product_id):
        api = "/api/positions/risk"

        json = {"product_id": product_id, "limit": limit}

        return self._send_requests("POST", api, auth_required=True, json=json)

    @_numeric_decorator
    def post_set_leverage(self, leverage_amount, product_id):
        api = "/api/positions/isolate"

        json = {"product_id": product_id, "leverage": leverage_amount}

        return self._send_requests("POST", api, auth_required=True, json=json)

    @_numeric_decorator
    def get_products_ticker(self, product_id):
        api = f"/api/products/{product_id}/ticker"
        return self._send_requests("GET", api)
