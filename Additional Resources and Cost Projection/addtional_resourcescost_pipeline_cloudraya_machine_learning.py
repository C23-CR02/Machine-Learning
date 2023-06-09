# -*- coding: utf-8 -*-
"""Addtional ResourcesCost Pipeline CloudRaya Machine Learning.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1vppv7sXt2jf__BCt55KXAYg38WkxzBiA
"""

# from google.colab import drive
# drive.mount('/content/drive')

# Commented out IPython magic to ensure Python compatibility.
import pandas as pd
import numpy as np
import sklearn
import matplotlib.pyplot as plt
import ast
import warnings
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error
from sklearn.metrics import mean_absolute_error
from itertools import groupby
from datetime import datetime, timedelta
from sklearn import metrics
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")
pd.options.mode.chained_assignment = None  # default='warn'
# %matplotlib inline

"""## Converting JSON Data into CSV"""

full_data_json = pd.read_json('response1.json')  # Data output dari Get API

res_list = []

for i in range(len(full_data_json)):
  res = full_data_json["data"][i]
  res_list.append(res)

json_full = pd.DataFrame.from_dict(res_list)[['date', 'hour', 'cpu_used']]
json_full['created_at'] = pd.to_datetime(json_full['date'])
json_full['created_at'] = json_full['created_at'] + pd.to_timedelta(json_full['hour'], unit='h')
json_full['cpu_used'] = json_full['cpu_used'] / 100
full_data = json_full[['created_at', 'cpu_used']]

"""### Train-Test Split"""

# Splitting the dataset
x_train, x_test, y_train, y_test = train_test_split(full_data.iloc[:, :-1], full_data.iloc[:, -1], 
                                                    test_size=0.2, shuffle=False)

"""## Modeling: ARIMA Univariate Time Series Forecasting

### ARIMA Model Hyperparameter Tuning
"""

# Evaluate an ARIMA model for a given order (p,d,q)
def evaluate_arima_model(df_train_y, df_test_y, arima_order):
    # Prepare training dataset
    train_size = int(len(df_train_y))
    test_size = int(len(df_test_y))
    train, test = df_train_y, df_test_y
    # Make predictions
    model = ARIMA(df_train_y, order=arima_order)
    model_fit = model.fit()
    predictions = model_fit.forecast(test_size)
    # Calculate out of sample error
    rmse = (mean_squared_error(test, predictions))**0.5
    mae = mean_absolute_error(test, predictions)
    return rmse, mae
 
# Evaluate combinations of p, d and q values for an ARIMA model
def evaluate_models(df_train_y, df_test_y, p_values, d_values, q_values):
    best_score, best_cfg, best_mae = float("inf"), None, float("inf")
    for p in p_values:
        for d in d_values:
            for q in q_values:
                order = (p,d,q)
                try:
                    rmse, mae = evaluate_arima_model(df_train_y, df_test_y, order)
                    if rmse < best_score:
                        best_score, best_cfg, best_mae = rmse, order, mae
                    print('ARIMA%s RMSE=%.7f MAE=%.7f' % (order,rmse,mae))
                except:
                    continue
    return best_cfg

# HATI-HATI LAMA
# Evaluate parameters

p_values = [1, 2, 3, 4]
d_values = [0, 1]
q_values = [1, 2, 3, 4]

p, d, q = evaluate_models(y_train, y_test, p_values, d_values, q_values)

"""#### Forecasting Future Values of CPU Usage"""

model = ARIMA(full_data['cpu_used'], order=(p,d,q))
model_fit = model.fit()

# Set the number of days to be forecasted
forecasted_days = 1

# Specify the starting timestamp
latest_timestamp = full_data.iloc[-1, 0]
interval = timedelta(minutes=60)

# Specify the number of times to increment the timestamp
num_times = int(forecasted_days * 24 * (60/60))

# Create an empty list to store the timestamps
timestamps = []

# Generate the timestamps
for i in range(1, num_times+1):
    timestamps.append(latest_timestamp + i * interval)

# Self-predict the exiting data with the trained-model
fitting = model_fit.predict(start=0, end=len(full_data)-1)


# Forecasting new data
forecasts = model_fit.forecast(int(forecasted_days * 24 * (60/60))).T

# Outputting the forecasted data (NECESSARY DATA [PROBABLY])
forecasts = pd.DataFrame({'Timestamp': timestamps, 'Forecasts': forecasts})

forecasts_json=forecasts.to_json(orient='records')

"""## Additional Resource Prediction"""

# Search for CPU Usage percentages that are equal or more than 80%
current_core = 1
core_upgrade_options = {1: 2,
                        2: 4,
                        4: 6,
                        6: 8}

need_add = forecasts[forecasts['Forecasts'] >= 0.8]
need_add['Forecasts'] = (need_add['Forecasts']*100).round(4)
need_add['Forecasts'] = need_add['Forecasts'].astype(str) + '%'

if need_add.empty:
  print(f"Your forecasted CPU Usage value in 24 hours ahead will be {forecasts['Forecasts'].iloc[-1] * 100:.4f}%")
else:
  print("Based on your usage pattern, you will reach more than 80% of your current available CPU core!")
  print(f"We recommend you to upgrade your CPU core to {core_upgrade_options[current_core]} CPU core(s)")
  print()
  print(need_add)

# Saving the list of forecasted data which will exceed current resource package
need_add.to_csv('exceeded_resource_data.csv', index=False)

# Saving the list of forecasted data which will exceed current resource package (as json)
need_add_json=need_add.to_json(orient='records')

"""## Cost Projection"""

forecasts_cost = forecasts.copy()

current_core = 1
core_upgrade_options = {1: 2,
                        2: 4,
                        4: 6,
                        6: 8}

cost_options = {1: round(85000/720, 2),
                2: round(200000/720, 2),
                4: round(700000/720, 2),
                6: round(720000/720, 2),
                8: round(1500000/720, 2)}

forecasts_cost['Core'] = current_core
forecasts_cost['Core'].loc[forecasts_cost['Forecasts'] >= 0.8] = core_upgrade_options[current_core]
forecasts_cost['Cost'] = forecasts_cost['Core'].map(cost_options)

## NECESSARY DATA (PROBABLY)
total_cost = forecasts_cost['Cost'].sum()

forecasts_cost_json = forecasts_cost.to_json(orient='records')

print(f'Total Estimated Forecasted Cost: Rp{total_cost:.2f}')

# Saving total estimated cost projection
forecasts_cost.to_csv('cost_projection.csv', index=False)