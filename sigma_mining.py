import math

from fair_price_constructor import FairPriceConstructor
from satis_api import SatisAPI


class SigmaMining:
    def __init__(self, satis_auth, json_config):
        self.currency_list = json_config["CURRENCY"]
        self.disabled_pairs = json_config["DISABLED_PAIRS"]
        self.satisAPI = SatisAPI(auth=satis_auth,
                                 currency_list=self.currency_list,
                                 disabled_pairs=self.disabled_pairs,
                                 )
        self.fair_price_constructor = FairPriceConstructor()
        self.LONG_SHORT_RATIO = json_config["LONG_SHORT_RATIO"]
        self.SPREAD = json_config["SPREAD"]
        self.LEVERAGE = json_config["LEVERAGE"]

    @classmethod
    def initializer(cls, satis_auth, json_config):
        """
        auto generate the useful info
        """
        sm = cls(satis_auth, json_config)

        # generate the useful info
        sm.products_dict_by_currency, sm.products_dict = sm.generate_products_info()
        sm.trading_fees_dict = sm.generate_trading_fee_dict()
        return sm

    def cancel_all_opened_orders(self):
        """
        cancel all opened orders
        """
        self.satisAPI.del_user_order()

    def check_locked_fund(self):
        """
        get the current balances
        """
        balances = self.satisAPI.get_accounts_all()
        balances_by_dict = {cur: None for cur in self.currency_list}
        for cur in self.currency_list:
            for balance in balances:
                if balance["currency"] == cur:
                    balances_by_dict[cur] = balance
                    break
        return balances_by_dict

    def exit_position(self, product_id):
        """
        close position by post a market order
        """

        cur_position = self.satisAPI.get_position(product_id)
        if not cur_position["is_open"]:
            # the position is closed
            return

        cur_size = cur_position["current_size"]
        if cur_size > 0:
            side = "sell"
        else:
            side = "buy"
        self.satisAPI.post_market_order(product_id, side, abs(cur_size), reduce_only=True)

    def exit_all_positions(self):
        """
        exit position one by one
        """
        for product_id in self.products_dict.keys():
            self.exit_position(product_id)

    def generate_products_info(self):
        """
        get the products info from API and fliter the products by the currency list
        """
        products_list = self.satisAPI.get_products()
        products_dict_by_currency = {cur: [] for cur in self.currency_list}
        products_dict = {}

        for product in products_list:
            if product in self.disabled_pairs:
                continue

            if product["status"] != "online":
                continue

            if product["settle_currency"] in self.currency_list:
                products_dict_by_currency[product["settle_currency"]].append(product["id"])
                products_dict[product["id"]] = product

        return products_dict_by_currency, products_dict

    def generate_trading_fee_dict(self):
        """
        generate the trading fee table 
        """
        trading_fees = self.satisAPI.get_trading_fees()
        return {fee["product_id"]: fee for fee in trading_fees}

    def get_currency_from_product(self, product_id):
        return self.products_dict[product_id]["settle_currency"]

    def apply_config_setting(self):
        self.cancel_all_opened_orders()
        self.exit_all_positions()
        for product_id in self.products_dict.keys():
            self.satisAPI.post_set_leverage(self.LEVERAGE, product_id)

    def get_opened_position_size(self, product_id):
        """
        get the position info and return the position side and size
        """
        cur_position = self.satisAPI.get_position(product_id)
        if cur_position["current_size"] > 0:
            return "Long", cur_position["current_size"]
        elif cur_position["current_size"] < 0:
            return "Short", cur_position["current_size"]
        else:
            return None, 0

    def order_placing_single_product(self, product_id, free_balance):
        """
        placing the order for a particular product 
        """

        def estimate_order_size_by_balance(balance, price, taker_fee_ratio):
            effective_balance = balance / (1 + taker_fee_ratio * 2)
            return round_decimals_down(effective_balance / price, 6)

        taker_fee_rate = self.trading_fees_dict[product_id]["taker_fee_rate"]
        #         last_fair_price = self.fair_price_constructor.get_fair_price(product_id)
        last_fair_price = self.satisAPI.get_products_ticker(product_id)["mark_price"]  # temporary
        opened_position_side, opened_position_size = self.get_opened_position_size(product_id)

        buy_side_fund = round_decimals_down(free_balance * self.LONG_SHORT_RATIO, 6)
        short_side_fund = round_decimals_down(free_balance * (1 - self.LONG_SHORT_RATIO), 6)

        buy_side_size = estimate_order_size_by_balance(buy_side_fund, last_fair_price - self.SPREAD, taker_fee_rate)
        short_side_size = estimate_order_size_by_balance(short_side_fund, last_fair_price + self.SPREAD, taker_fee_rate)

        if opened_position_side == "Long":
            self.satisAPI.post_limit_order(product_id, "sell", opened_position_size, last_fair_price + self.SPREAD,
                                           reduce_only=True)

        elif opened_position_side == "Short":
            self.satisAPI.post_limit_order(product_id, "buy", opened_position_size, last_fair_price - self.SPREAD,
                                           reduce_only=True)

        self.satisAPI.post_limit_order(product_id, "buy", buy_side_size, last_fair_price - self.SPREAD)
        self.satisAPI.post_limit_order(product_id, "sell", short_side_size, last_fair_price + self.SPREAD)

    def order_placing(self):
        """
        placing order for all selected products 
        """
        self.cancel_all_opened_orders()

        funds = self.check_locked_fund()
        for currency in self.currency_list:
            sub_fund = funds[currency]
            sub_product_list = self.products_dict_by_currency[currency]

            if not sub_fund or not sub_product_list:
                continue

            balance_per_product = sub_fund["locked"] / len(sub_product_list)

            for product in sub_product_list:
                self.order_placing_single_product(product, balance_per_product)

    def min_update_delay(self, update_delay):
        """
        return the min update delay if update_delay is too short
        """
        action_per_cycle = 3 + 4 * len(self.products_dict)
        return max(action_per_cycle / 30, update_delay)

    def get_reward_amount(self):
        pass


def round_decimals_down(number: float, decimals: int = 2):
    """
    Returns a value rounded down to a specific number of decimal places.
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    elif decimals == 0:
        return math.floor(number)

    factor = 10 ** decimals
    return math.floor(number * factor) / factor
