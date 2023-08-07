import json
import pandas as pd
import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt

class FIREBaseClass():
    def plot(self, fig = None, ax = None):
        if fig is None: fig = plt.gcf()
        if ax is None: ax = plt.gca()
        return fig, ax


class FIREArray(dict):
    def __init__(self, array_of, json_file):
        with open(json_file) as f:
            target_scenario_arr = json.load(f)
        for k,v in target_scenario_arr.items():
            self[k] = array_of(v, name=k)

    def select(self, scenario_str):
        return self[scenario_str]


class FIREInvestment(FIREBaseClass):
    def __init__(self, setts_dict, name = ""):
        self._investment_opportunities = setts_dict["investment_opportunities"]
        self._investment_structure_var = setts_dict["investment_structure_var"]
        self._investment_structure_fix = setts_dict["investment_structure_fix"]
        self._initial_assets = setts_dict["initial_assets"]
        self._investments_monthly = setts_dict["investments_monthly"]
        self._investment_yearly_growth_perc = setts_dict["investment_var_yearly_growth_perc"]

        self._investment_var_df = self._assemble_investment_df(self._investment_opportunities, self._investment_structure_var, self._investments_monthly)
        self._investment_fix_df = self._assemble_investment_df(self._investment_opportunities, self._investment_structure_fix, self._initial_assets)


    @property
    def investment_var_df(self):
        return self._investment_var_df

    @property
    def investment_fix_df(self):
        return self._investment_fix_df

    @property
    def investment_fix_average_returns(self):
        return self._calc_average_yield("FIX")[0]

    @property
    def investment_fix_average_returns(self):
        return self._calc_average_yield("VAR")[0]

    def _get_investment_df(self, desc):
        _inv = {"FIX":self.investment_fix_df, "VAR":self.investment_var_df}
        return _inv[desc]

    def _calc_average_yield(self, desc):
        investments_df = self._get_investment_df(desc)
        total_share = investments_df.share.sum()
        avg_yield = (investments_df.share * investments_df.yield_per_year_perc).sum() / total_share
        return avg_yield, total_share

    def _assemble_investment_df(self, investment_opportunities, investment_structure, total_investments):
        _investment_opp_df = pd.DataFrame(investment_opportunities).T
        _investment_structure_df = pd.DataFrame(investment_structure, columns = ["share", "type"]) 
        _investments_df = pd.merge(_investment_structure_df,_investment_opp_df, left_on="type",right_index=True,how="left")
        _investments_df["share_total"] = _investments_df.share * total_investments
        return _investments_df

    def plot_portfolio_performance(self, desc, max_time = 10, ref_value = 1000, fig = None, ax = None):
        fig, ax = super(FIREInvestment,self).plot(fig, ax)
        pers = np.arange(0,max_time+1,1)
        investments_df = self._get_investment_df(desc)
        avg_yield, total_share = self._calc_average_yield(desc)
        
        for ii, row in investments_df.iterrows():
            ax.plot( pers, npf.fv(row.yield_per_year_perc/100., pers, 0, -ref_value), ls="-", label = f"{row.type}, growth = {row.yield_per_year_perc:.2f}%" )
        ax.plot( pers, npf.fv(avg_yield/100., pers, 0, -ref_value), ls="--", c="black", label = f"Portfolio (weighted average), growth = {avg_yield:.2f}%" )
        ax.legend()
        ax.set_xlabel("Time / [years]")
        ax.set_ylabel("Value / [€]")
        ax.set_title(f"Performance of reference investment = {ref_value}€ over time")
        return self

class FIREInvestmentArray(FIREArray):
    def __init__(self, *args, **kwargs):
        super(FIREInvestmentArray,self).__init__(FIREInvestment, *args, **kwargs)


class FIRETarget(FIREBaseClass):
    def __init__(self, setts_dict, name = ""):
        self._target_value_arr = setts_dict["target_value_arr"]
        self._withdrawal_rate_perc = setts_dict["withdrawal_rate_perc"]
        self._target_df = pd.DataFrame(self._target_value_arr).T
        self._name = name

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
        fig, ax = super(FIRETarget,self).plot(fig, ax)
        target_value_total_ret_nom = self.calc_target_value()

        ax.set_title(f"Total value at retirement: {int(target_value_total_ret_nom)}€ (nominal)\nFIRE factor = {int(self.fire_factor)}")
        self._target_df.value_ret_nom.plot.pie(autopct='%1.1f%%',startangle=90)
        ax.set_ylabel("Nominal value / [€]")

        return self

class FIRETargetArray(FIREArray):
    def __init__(self, *args, **kwargs):
        super(FIRETargetArray,self).__init__(FIRETarget, *args, **kwargs)


class FIREExternalConditions(FIREBaseClass):
    def __init__(self, setts_dict, name = ""):
        self._average_inflation_rate_perc = setts_dict["average_inflation_rate_perc"]
        self._start_age = setts_dict["start_age"]
        self._capital_tax_rate_perc = setts_dict["capital_tax_rate_perc"]
        self._name = name

    @property
    def inflation_rate_average_perc(self):
        return self._average_inflation_rate_perc

class FIREExternalConditionsArray(FIREArray):
    def __init__(self, *args, **kwargs):
        super(FIREExternalConditionsArray,self).__init__(FIREExternalConditions, *args, **kwargs)

class FIRESimulation(FIREBaseClass):
    def __init__(self, investments, target, conditions):
        self._investments = investments
        self._target = target
        self._conditions = conditions

    @property
    def investments(self):
        return self._investments

    @property
    def target(self):
        return self._target

    @property
    def conditions(self):
        return self._conditions
    
    def plot_growth_rates(self, fig = None, ax = None, perc_thres = 0.5):
        fig, ax = super(FIRESimulation,self).plot(fig, ax)
        avg_yield_real = self.investments.investment_fix_average_returns
        avg_yield_nominal = avg_yield_real - self.conditions.inflation_rate_average_perc
        avg_yield_withdr_real = avg_yield_real - self.target.withdrawal_rate_perc
        avg_yield_withdr_nominal = avg_yield_real - self.target.withdrawal_rate_perc - self.conditions.inflation_rate_average_perc

        description = [ 'Real average returns',
                        'Nominal average returns\nconsidering effects of inflation',
                        'Real average returns\nconsidering retirement withdrawals',
                        'Nominal average returns\nconsidering retirement withdrawals']
        values = [avg_yield_real, avg_yield_nominal, avg_yield_withdr_real, avg_yield_withdr_nominal]

        ax.bar(description,values)
        for ii,(d,v) in enumerate(zip(description, values)):
            col = "black"
            add_text = ""
            if v<perc_thres: col = "red"
            if v<0: add_text = " (yearly net loss!)"
            plt.text(ii, v,f"{v:.2f}%{add_text}", ha = 'center', va='bottom', c=col)

        ax.set_ylabel("Returns / [%]")

        return self

        #total_share = investments_df.share.sum()
#avg_yield = (investments_df.share * investments_df.yield_per_year_perc).sum() / total_share
#
#print(f"Investing {total_share*100}% of {investments_monthly}€ at an average yield of {avg_yield}% per year.")
#avg_yield -= average_inflation_rate_perc
#print(f"Considering an average inflation rate of {average_inflation_rate_perc}%, the nominal average yield is {avg_yield}% per year.")
#print(f"With a withdrawal rate of {withdrawal_rate}%, net gain/loss during retirement each year will be {avg_yield-withdrawal_rate}%.")
#if avg_yield-withdrawal_rate < 0:
#    print("WARING: yearly net loss expected during retirement!")
