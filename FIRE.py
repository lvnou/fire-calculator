import json
import pandas as pd
import matplotlib.pyplot as plt

class FIRETargetArray(dict):
    def __init__(self, json_file):
        # Target
        #target_scenario_str = "SCENARIO_INCOME_AGGRESSIVE"
        with open(json_file) as f:
            target_scenario_arr = json.load(f)
        for k,v in target_scenario_arr.items():
            self[k] = FIRETarget(v, name=k)

    def select_target(self, target_scenario_str):
        return self[target_scenario_str]

class FIRETarget:
    def __init__(self, setts_dict, name = ""):
        self._target_value_arr = setts_dict["target_value_arr"]
        self._withdrawal_rate_perc = setts_dict["withdrawal_rate_perc"]
        self._target_df = pd.DataFrame(self._target_value_arr).T


    def calc_target_value(self):
        valuation_factor_ret_nom = {"MONTHLY": self.fire_factor*12., "YEARLY": self.fire_factor, "ONE_TIME":1.} # valuation to convert into nominal value at retirement
        self._target_df["value_ret_nom"] =  self._target_df.value * self._target_df.frequency.apply(lambda x: valuation_factor_ret_nom[x])
        target_value_total_ret_nom =  self._target_df.value_ret_nom.sum()
        return target_value_total_ret_nom

    @property
    def fire_factor(self):
        return 1./(self.withdrawal_rate_perc/100.)

    @property
    def withdrawal_rate_perc(self):
        return self._withdrawal_rate_perc

    @property
    def target_value_arr(self):
        return self._target_value_arr
    
    def plot_pie_value(self, fig = None, ax = None):
        if fig is None: fig = plt.gcf()
        if ax is None: ax = plt.gca()
        
        target_value_total_ret_nom = self.calc_target_value()

        ax.set_title(f"Total value at retirement: {int(target_value_total_ret_nom)}€ (nominal)\nFIRE factor = {int(self.fire_factor)}")
        self._target_df.value_ret_nom.plot.pie(autopct='%1.1f%%',startangle=90)
        ax.set_ylabel("Nominal value / [€]")

        return self
