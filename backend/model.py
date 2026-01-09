import pandas as pd
from sklearn.tree import DecisionTreeRegressor
from sklearn.preprocessing import LabelEncoder

# Load dataset
data = pd.read_csv("traffic_data.csv")

# Encode categorical columns
le_traffic = LabelEncoder()
le_accident = LabelEncoder()

data["traffic_density"] = le_traffic.fit_transform(data["traffic_density"])
data["accident_zone"] = le_accident.fit_transform(data["accident_zone"])

X = data[["traffic_density", "accident_zone"]]
y = data["wait_time"]

# Train model
model = DecisionTreeRegressor()
model.fit(X, y)

def predict_wait_time(traffic_density, accident_zone):
    t = le_traffic.transform([traffic_density])[0]
    a = le_accident.transform([accident_zone])[0]
    return int(model.predict([[t, a]])[0])
