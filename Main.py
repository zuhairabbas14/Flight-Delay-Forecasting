# Imports

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.pipeline import Pipeline
import sklearn.metrics as metrics
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import PolynomialFeatures
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn import decomposition, preprocessing, feature_selection, linear_model, model_selection


# Function that returns evaluation scores of the model

def get_scores(name, y_test, y_pred):
  mse_score = metrics.mean_squared_error(y_test, y_pred)
  mae_score = metrics.mean_absolute_error(y_test, y_pred)
  r2_score = metrics.r2_score(y_test, y_pred)
  return [name, mse_score, mae_score, r2_score]

# Reading Dataset

df = pd.read_csv('flight_delay.csv')
df.head()

# Expanding Departure and Arrival timestamps columns into days, months, years and flight duration

departure_series = pd.to_datetime(df['Scheduled depature time'])
arrival_series = pd.to_datetime(df['Scheduled arrival time'])

# Adding flight duration column

df['Flight duration'] = [abs(x).total_seconds() / 3600.0 for x in (departure_series - arrival_series)]

# Expanding Departure timestamps

df['Depature year'] = departure_series.dt.year
df['Depature month'] = departure_series.dt.month
df['Depature day'] = departure_series.dt.day
df['Depature weekday'] = departure_series.dt.dayofweek
df['Depature hour'] = departure_series.dt.hour
df.drop('Scheduled depature time', inplace=True, axis=1)

# Using only hours from arrival timestamp

df['Arrival hour'] = arrival_series.dt.hour
df.drop('Scheduled arrival time', inplace=True, axis=1)

# Detecting and Removing Outliers using The interquartile range (IQR)

Q1 = df.quantile(0.25)
Q3 = df.quantile(0.75)
IQR = Q3 - Q1
df = df[~((df < (Q1 - 1.5 * IQR)) |(df > (Q3 + 1.5 * IQR))).any(axis=1)]

# One hot encoding the Airport names

df = pd.get_dummies(df, columns = ['Depature Airport', 'Destination Airport'], drop_first=True)

# Moving target column to the end

df['Delay'] = df.pop('Delay')

# Splitting the Dataset into training and testing

mask = df['Depature year'] == 2018

df_train = df[~mask]
df_test = df[mask]

# Scaling the training data using Robust Scalar (Robust to Outliers)

scalerX = preprocessing.RobustScaler(quantile_range=(25.0, 75.0))
X = scalerX.fit_transform(df_train.drop("Delay", axis=1))
df_train_scaled = pd.DataFrame(X, columns=df_train.drop("Delay", axis=1).columns, index=df_train.index)
x_test = scalerX.fit_transform(df_test.drop("Delay", axis=1))
df_test_scaled = pd.DataFrame(x_test, columns=df_test.drop("Delay", axis=1).columns, index=df_test.index)

scalerY = preprocessing.RobustScaler(quantile_range=(25.0, 75.0))
df_train_scaled['Delay'] = scalerY.fit_transform(df_train['Delay'].values.reshape(-1,1))
df_test_scaled['Delay'] = scalerY.fit_transform(df_test['Delay'].values.reshape(-1,1))

# Feature selection 

X = df_train_scaled.drop('Delay', axis=1).values
y = df_train_scaled['Delay'].values
feature_names = df_train_scaled.drop('Delay', axis=1).columns

# P-value

selector = feature_selection.SelectKBest(score_func=  
               feature_selection.f_regression, k=7).fit(X,y)
pvalue_selected_features = feature_names[selector.get_support()]

# Regularization

selector = feature_selection.SelectFromModel(estimator= 
              linear_model.Ridge(alpha=1.0, fit_intercept=True), 
                                 max_features=7).fit(X,y)
regularization_selected_features = feature_names[selector.get_support()]

# Using only the selected features

X_names = list(set(list(set(pvalue_selected_features) or set(regularization_selected_features))))
X_train = df_train_scaled[X_names].values
y_train = df_train_scaled['Delay'].to_numpy()
X_test = df_test_scaled[X_names].values
y_test = df_test_scaled['Delay'].to_numpy()

# Training and evaluating 3 different models

ridge = linear_model.Ridge()
decision_tree = DecisionTreeRegressor()
polynomial_features = PolynomialFeatures(2)
linear_regression = linear_model.LinearRegression()
polynomial_regression = Pipeline([("polynomial_features", polynomial_features), ("linear_regression", linear_regression)])
models = {'Ridge Regression' : ridge, 'Polynomial Regression' :polynomial_regression, 'Decision Tree Regression' : decision_tree}

training_errors, testing_errors = [], []

for name, model in models.items():
  model.fit(X_train, y_train)
  y_pred_train = model.predict(X_train)
  y_pred_test = model.predict(X_test)
  training_errors.append(get_scores(name, y_pred_train, y_train))
  testing_errors.append(get_scores(name, y_pred_test, y_test))

# Putting the scores into a Dataframe

score_columns = ['Model', 'MSE_train', 'MAE_train', 'R2_train', 'MSE_test', 'MAE_test', 'R2_test']
train_test_errors = [training_errors[x] + testing_errors[x][1:] for x in range(len(training_errors))]
score_df = pd.DataFrame(train_test_errors, columns=score_columns)
score_df
