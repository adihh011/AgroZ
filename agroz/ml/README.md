# Real ML model path

Use a properly labelled crop recommendation CSV with:
`N,P,K,temperature,humidity,ph,rainfall,label`

Then run:

```cmd
python ml/train_model.py data\crop_recommendation.csv
```

The script prints validation accuracy and saves `model/crop_model.joblib`.
Do not copy an accuracy number into the UI unless the dataset split and validation procedure justify it.
