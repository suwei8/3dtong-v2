"""Ten one-vs-rest probability classifiers trained on preceding draws."""
import numpy as np

class XGBoostPredictor:
    name="xgboost"
    def fit(self,X,Y):
        from xgboost import XGBClassifier
        self.models=[]
        for d in range(10):
            m=XGBClassifier(n_estimators=55,max_depth=2,learning_rate=.07,
                            min_child_weight=18,reg_lambda=25,subsample=.9,
                            colsample_bytree=.9,tree_method="hist",
                            n_jobs=2,random_state=2026,objective="binary:logistic")
            m.fit(X,Y[:,d])
            self.models.append(m)
        return self
    def predict_proba(self,X):
        return np.column_stack([m.predict_proba(X)[:,1] for m in self.models])
