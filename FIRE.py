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
    def investment_var_yearly_growth_perc(self):
        return self._investment_yearly_growth_perc

    @property
    def investment_var_df(self):
        return self._investment_var_df

    @investment_var_df.setter
    def investment_var_df(self, df):
        self._investment_var_df = df
        return self

    @property
    def investment_fix_df(self):
        return self._investment_fix_df

    @investment_fix_df.setter
    def investment_fix_df(self, df):
        self._investment_fix_df = df
        return self

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
        _investments_df["value"] = _investments_df.share * total_investments
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

    @property
    def expenses_fixed_total(self):
        value_onetime_expense = self._target_df[self._target_df.frequency == "ONE_TIME"].value.sum()
        return value_onetime_expense

    @property
    def expenses_variable_yearly(self):
        value_yearly_expense = self._target_df[self._target_df.frequency == "YEARLY"].value.sum()
        return value_yearly_expense

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
        self._tax_mode = setts_dict["tax_mode"]

    @property
    def inflation_rate_average_perc(self):
        return self._average_inflation_rate_perc

    @property
    def start_age(self):
        return self._start_age

    @property
    def capital_tax_rate_perc(self):
        return self._capital_tax_rate_perc

    @property
    def tax_mode(self):
        """
        Either "TAX_ALL_GAINS" or "TAX_ON_REALIZATION"
        """
        return self._tax_mode

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
    

    def _reset_simulation(self):
        initial_investments = self.investments.investment_fix_df
        initial_investments = initial_investments[initial_investments.yield_per_year_perc > 0.0]
        var_investments = self.investments.investment_var_df
        var_investments_cum = self.investments.investment_var_df.copy()
        var_investments_cum["value"] = 0

        self._sim_res = {
                "fixed_invest_valuation" : [],
                "var_investments_cum_valuation" : [],
                "var_investments": [],
                "total_valuation" : [], "fixed_total_valuation":[], "var_total_valuation":[], "var_valuation": [],
          "time" : [],
          "is_ret": [],
          "ret_time":None,
          "taxes_cum" : [0]
          }
        
        self._update_sim_vars(0,initial_investments.copy(), var_investments_cum.copy(), var_investments.copy())
        
        return self

    def _tax_corrected_expense(self, expense):
        if self.conditions.tax_mode == "TAX_ON_REALIZATION":
            expense = expense/(1-self.conditions.capital_tax_rate_perc/100)
        return expense

    @property
    def target_value(self):
        return self._tax_corrected_expense(self.target.calc_target_value())

    def _calc_sim_aux_vars(self):
        self._sim_res["fixed_total_valuation"].append(self._sim_res["fixed_invest_valuation"][-1].value.sum())
        self._sim_res["var_total_valuation"].append(self._sim_res["var_investments_cum_valuation"][-1].value.sum())
        self._sim_res["var_valuation"].append(self._sim_res["var_investments"][-1].value.sum())
        self._sim_res["total_valuation"].append(self._sim_res["fixed_total_valuation"][-1] + self._sim_res["var_total_valuation"][-1])
        
        if len(self._sim_res["is_ret"]) == 0: was_ret = False
        else: was_ret = self._sim_res["is_ret"][-1]
        self._sim_res["is_ret"].append( ((self._sim_res["total_valuation"][-1] >= self.target_value) or was_ret) )
        if self._sim_res["is_ret"][-1] and not self._sim_res["is_ret"][-2]:
            self._sim_res["ret_time"] = self._sim_res["time"][-1]
        return self

    def _update_sim_vars(self, time, fixed_invest_valuation, var_investments_cum_valuation, var_investments):
        self._sim_res["fixed_invest_valuation"].append(fixed_invest_valuation)
        self._sim_res["var_investments_cum_valuation"].append(var_investments_cum_valuation)
        self._sim_res["var_investments"].append(var_investments)
        self._sim_res["time"].append(time)
        self._calc_sim_aux_vars()
        return self

    def _tax_capital_income(self, value_df_i, value_df_im1):
        if self.conditions.tax_mode == "TAX_ALL_GAINS":
            v_tax = self.conditions.capital_tax_rate_perc/100*(value_df_i.value - value_df_im1.value)
            value_df_i.value = value_df_i.value - v_tax
        return value_df_i

    def _retirement_expenses(self, was_ret):
            if not was_ret: return 0, (0,0)
            exp_monthly = self.target.expenses_variable_yearly / 12.
            exp_extra_f, exp_extra_v = 0,0
            if not self._sim_res["is_ret"][-2]:
                exp_extra = self.target.expenses_fixed_total
                # seperate one-time expense based on share of fixed and variable investment
                val_f, val_v = self._sim_res["fixed_total_valuation"][-1], self._sim_res["var_total_valuation"][-1]
                exp_extra_f, exp_extra_v = val_f/(val_f+val_v)* exp_extra, val_v/(val_f+val_v)* exp_extra
            
            return self._tax_corrected_expense(exp_monthly), (self._tax_corrected_expense(exp_extra_f), self._tax_corrected_expense(exp_extra_v))

    def _recurring_investments(self, was_ret, i_i):
            if was_ret:
                i_i.value = 0.0
            else:
                i_i.value = i_i.value *(1.+self.investments.investment_var_yearly_growth_perc/100.)
            i_i["yield_per_month"] = i_i.yield_per_year_perc/100./12.
            return i_i

    def perform(self, max_time = 70):
        self._reset_simulation()

        for p in range(1,1+max_time):
            was_ret = self._sim_res["is_ret"][-1]
            
            vf_im1,vv_im1, i_im1 = self._sim_res["fixed_invest_valuation"][-1], self._sim_res["var_investments_cum_valuation"][-1], self._sim_res["var_investments"][-1]
            i_i = i_im1.copy(); vv_i=vv_im1.copy(); vf_i=vf_im1.copy()

            exp_monthly, (exp_extra_f, exp_extra_v) = self._retirement_expenses(was_ret)
            i_i = self._recurring_investments(was_ret, i_i)

            i_i["value_yearly"] = npf.fv(i_i.yield_per_month, 12, -i_i.value + exp_monthly, -0, when="begin") ## annualize monthly returns: https://financetrain.com/how-to-annualize-monthly-returns-example
            
            vv_i.value = npf.fv(vv_i.yield_per_year_perc/100., 1, -i_i.value_yearly+exp_extra_v*i_i.share, -vv_im1.value, when="end")
            vf_i.value = npf.fv(vf_i.yield_per_year_perc/100., 1, 0.0, -vf_im1.value+exp_extra_f*vf_i.share, when="end")
                
            vv_i = self._tax_capital_income(vv_i, vv_im1)
            vf_i = self._tax_capital_income(vf_i, vf_im1)

            self._update_sim_vars(p, vf_i, vv_i, i_i)
        return self._sim_res



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

    @property
    def simulation_results(self):
        return self._sim_res

    @property
    def simulation_retirement_time(self):
        return self.simulation_results["ret_time"]

    @property
    def simulation_retirement_age(self):
        return self.simulation_results["ret_time"] + self.conditions.start_age

    def plot_value_over_time(self,fig=None, ax=None):
        fig, ax = super(FIRESimulation,self).plot(fig, ax)
        retirement_time, retirement_age = self.simulation_results["ret_time"],self.simulation_results["ret_time"] + self.conditions.start_age
        if retirement_time is None: ax.set_title(f"FIRE calculation, no retirement in selected time span")    
        else:   ax.set_title(f"FIRE calculation, retire after {retirement_time} years, age {retirement_age}")
        time_arr, val_arr = self.simulation_results["time"], self.simulation_results["total_valuation"]
        ax.plot(time_arr, val_arr, label = "Portfolio value", c="blue")
        ax.plot(time_arr, [self.target.calc_target_value() for i in time_arr],label = "FIRE target",c="red")
        if retirement_time is not None:
            ax.axvline(retirement_time, c="black",ls="--")
        ax.legend()
        ax.set_xlabel("Time / [years]")
        ax.set_ylabel("Value / [€]")
        
        ax2=plt.twiny()
        ax2.plot(np.array(time_arr)+self.conditions.start_age,val_arr,alpha=1)
        ax2.set_ylabel("Age / [years]")
        
        return self


    def plot_value_components_over_time(self, fig = None, ax = None):
        fig, ax = super(FIRESimulation,self).plot(fig, ax)
        ax.set_title(f"Investment value over time, in components")
        time_arr, val_arr = self.simulation_results["time"], self.simulation_results["total_valuation"]
        
        initial_fixed_value = self.simulation_results["fixed_total_valuation"][0]
        fixed_value_growth = np.array(self.simulation_results["fixed_total_valuation"]) - initial_fixed_value
        var_value_cum = np.cumsum(self.simulation_results["var_valuation"]) * 12.
        var_value_growth = np.array(self.simulation_results["var_total_valuation"]) - var_value_cum

        ax.plot(time_arr, val_arr, label = "Total value", c="black")

        ax.plot(time_arr, [initial_fixed_value for i in time_arr], label = "Initial investment", c="blue", alpha = 0.75, ls = "--")
        ax.plot(time_arr, fixed_value_growth, label = "Growth from initial investment", c="blue", alpha = 0.25, ls = "--")
        ax.plot(time_arr, self.simulation_results["fixed_total_valuation"], label = "Initial investment, total", c="blue", alpha = 1, ls = "-")
        
        ax.plot(time_arr, var_value_cum, label = "Recurring investments", c="red", alpha = 0.75, ls = "--")
        ax.plot(time_arr, var_value_growth, label = "Growth from recurring investment", c="red", alpha = 0.25, ls = "--")
        ax.plot(time_arr, self.simulation_results["var_total_valuation"], label = "Recurring investment, total", c="red", alpha = 1, ls = "-")
        
        ax.set_xlabel("Time / [years]")
        ax.set_ylabel("Investment / [€]")
        ax.legend()

        return self

    def plot_investments_over_time(self, fig = None, ax = None):
        fig, ax = super(FIRESimulation,self).plot(fig, ax)
        ax.set_title(f"Montly investments over time ({self.investments.investment_var_yearly_growth_perc}% yearly growth)")
        ax.plot(self.simulation_results["time"], self.simulation_results["var_valuation"])
        ax.set_xlabel("Time / [years]")
        ax.set_ylabel("Investment / [€]")

        return self
