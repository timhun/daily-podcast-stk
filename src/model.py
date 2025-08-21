import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

def train_model(df):
    X = df[["SMA_10", "RSI", "Return"]]
    y = df["Target"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, shuffle=False, test_size=0.2)

    model = lgb.LGBMClassifier()
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)

    joblib.dump(model, "model.pkl")
    return acc

if __name__ == "__main__":
    import data, features
    df = data.fetch_data()
    df = features.add_features(df)
    acc = train_model(df)
    print("Accuracy:", acc)
