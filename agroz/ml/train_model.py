"""Train a real Random Forest crop model from a labelled CSV.

Expected columns:
N,P,K,temperature,humidity,ph,rainfall,label

Usage:
python ml/train_model.py data/crop_recommendation.csv
"""
import os, sys, joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

if len(sys.argv) != 2:
    raise SystemExit("Usage: python ml/train_model.py path/to/crop_recommendation.csv")
path=sys.argv[1]
df=pd.read_csv(path)
required=["N","P","K","temperature","humidity","ph","rainfall","label"]
missing=[x for x in required if x not in df.columns]
if missing: raise SystemExit(f"Missing columns: {missing}")
X=df[["N","P","K","temperature","humidity","ph","rainfall"]]
y=df["label"]
X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=.2,random_state=42,stratify=y)
model=RandomForestClassifier(n_estimators=300,random_state=42,n_jobs=-1,class_weight="balanced")
model.fit(X_train,y_train)
pred=model.predict(X_test)
print("Validation accuracy:",round(accuracy_score(y_test,pred)*100,2),"%")
print(classification_report(y_test,pred))
os.makedirs("model",exist_ok=True)
joblib.dump(model,"model/crop_model.joblib")
print("Saved model/crop_model.joblib")
